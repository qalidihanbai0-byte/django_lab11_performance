import os
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from .guard import NO_ANSWER_SQL, UnsafeSQLError, extract_sql, run_readonly, validate_sql
from .llm import ask_llm, ask_sql
from .prompts import build_system_prompt


class SQLGuardTests(SimpleTestCase):
    def test_extracts_plain_and_fenced_sql(self):
        self.assertEqual(extract_sql('  SELECT 1;  '), 'SELECT 1;')
        self.assertEqual(extract_sql('```SQLite\r\nSELECT 1;\r\n```'), 'SELECT 1;')
        for response in ('', '  ', None, '```sql\n \n```'):
            with self.subTest(response=response), self.assertRaises(UnsafeSQLError):
                extract_sql(response)

    def test_validates_aggregates_and_caps_limit(self):
        sql = (
            'SELECT c.city, COUNT(o.id) AS orders, SUM(i.quantity * i.price) AS revenue '
            'FROM shop_customer AS c JOIN shop_order AS o ON c.id = o.customer_id '
            'JOIN shop_orderitem AS i ON i.order_id = o.id '
            "WHERE o.status = 'paid' GROUP BY c.city ORDER BY revenue DESC"
        )
        self.assertTrue(validate_sql(sql).endswith('LIMIT 100'))
        self.assertTrue(validate_sql(sql + ' LIMIT 200').endswith('LIMIT 100'))
        self.assertTrue(validate_sql(sql + ' LIMIT 5').endswith('LIMIT 5'))
        self.assertEqual(validate_sql(NO_ANSWER_SQL + ';'), NO_ANSWER_SQL)

    def test_rejects_writes_unapproved_data_and_unsupported_selects(self):
        rejected = (
            'INSERT INTO shop_customer (name, city) VALUES (NULL, NULL)',
            'UPDATE shop_customer SET city = NULL',
            'DELETE FROM shop_customer',
            'DROP TABLE shop_customer',
            'ALTER TABLE shop_customer RENAME TO customer',
            'CREATE TABLE sample (id INTEGER)',
            "ATTACH DATABASE ':memory:' AS sample",
            'PRAGMA query_only',
            'SELECT 1; SELECT 2',
            'SELECT 1; DROP TABLE shop_customer',
            'SELECT * FROM auth_user',
            'SELECT * FROM blog_post',
            'SELECT * FROM shop_querylog',
            'SELECT * FROM main.shop_customer',
            'SELECT missing FROM shop_customer',
            'SELECT c.missing FROM shop_customer AS c',
            'SELECT rowid FROM shop_customer',
            'SELECT id FROM shop_customer JOIN shop_order ON shop_customer.id = shop_order.customer_id',
            'WITH x AS (DELETE FROM shop_customer RETURNING id) SELECT * FROM x',
            'WITH x AS (SELECT id FROM shop_customer) SELECT * FROM x',
            'SELECT id FROM shop_customer UNION SELECT id FROM shop_order',
            'SELECT id FROM shop_customer WHERE id IN (SELECT id FROM shop_order)',
            'SELECT /* comment */ id FROM shop_customer',
            'SELECT id FROM shop_customer -- comment',
            'SELECT * FROM pragma_table_info(\'shop_customer\')',
            "SELECT load_extension('example')",
            'SELECT id FROM shop_customer LIMIT -1',
            'SELECT id FROM shop_customer LIMIT 1 + 2',
        )
        for sql in rejected:
            with self.subTest(sql=sql), self.assertRaises(UnsafeSQLError):
                validate_sql(sql)


class ReadOnlyQueryTests(SimpleTestCase):
    def setUp(self):
        workspace = TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.db_path = Path(workspace.name) / 'test database.sqlite3'
        settings_patch = patch('shop.guard.settings')
        guard_settings = settings_patch.start()
        self.addCleanup(settings_patch.stop)
        guard_settings.DATABASES = {'default': {'NAME': self.db_path}}
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.executescript('''
                CREATE TABLE shop_customer (id INTEGER PRIMARY KEY, name TEXT, city TEXT);
                CREATE TABLE shop_order (id INTEGER PRIMARY KEY, customer_id INTEGER, status TEXT, created_at TEXT);
                CREATE TABLE shop_orderitem (id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER,
                                             quantity INTEGER, price DECIMAL);
                CREATE TABLE auth_user (id INTEGER PRIMARY KEY);
                INSERT INTO shop_order VALUES
                    (1, 1, 'paid', '2026-10-01'), (2, 1, 'cancelled', '2026-10-01');
                INSERT INTO shop_orderitem VALUES (1, 1, 1, 3, 125.50), (2, 2, 1, 1, 200);
            ''')
            db.executemany(
                'INSERT INTO shop_customer (name, city) VALUES (?, ?)',
                [('Customer', 'Almaty')] * 120,
            )

    def test_reads_aggregates_and_limits_results(self):
        columns, rows = run_readonly(
            'SELECT c.city, COUNT(o.id) AS orders, SUM(i.quantity * i.price) AS revenue '
            'FROM shop_customer c JOIN shop_order o ON c.id = o.customer_id '
            'JOIN shop_orderitem i ON i.order_id = o.id '
            "WHERE o.status = 'paid' GROUP BY c.city"
        )
        self.assertEqual(columns, ['city', 'orders', 'revenue'])
        self.assertEqual(rows, [('Almaty', 1, 376.5)])
        self.assertEqual(run_readonly('SELECT COUNT(*) FROM shop_customer')[1], [(120,)])
        self.assertEqual(len(run_readonly('SELECT id FROM shop_customer ORDER BY id')[1]), 100)
        self.assertEqual(run_readonly(NO_ANSWER_SQL), ([], []))

    def test_rejected_writes_leave_database_unchanged(self):
        before = self.db_path.read_bytes()
        sql = 'DELETE FROM shop_customer'
        with self.assertRaises(UnsafeSQLError):
            run_readonly(sql)
        # Exercise the connection's own restrictions independent of the parser.
        with patch('shop.guard.validate_sql', side_effect=lambda query: query):
            for denied in (sql, 'SELECT id FROM auth_user'):
                with self.subTest(sql=denied), self.assertRaises(sqlite3.DatabaseError):
                    run_readonly(denied)
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_execution_deadline_interrupts_query(self):
        with patch('shop.guard.QUERY_TIMEOUT_SECONDS', 0):
            with self.assertRaisesRegex(sqlite3.OperationalError, 'interrupted'):
                run_readonly(
                    'SELECT COUNT(*) FROM shop_customer a CROSS JOIN shop_customer b'
                )


class LLMTests(SimpleTestCase):
    def test_prompt_modes(self):
        baseline = build_system_prompt('baseline')
        improved = build_system_prompt('improved')
        self.assertTrue(improved.startswith(baseline))
        for fragment in ('shop_orderitem.order_id -> shop_order.id', 'LIMIT 100', 'NO_ANSWER'):
            self.assertIn(fragment, baseline)
        for fragment in ("status = 'paid'", 'KZT', 'Question:'):
            self.assertIn(fragment, improved)
            self.assertNotIn(fragment, baseline)
        for private_table in ('shop_querylog', 'blog_post', 'auth_user'):
            self.assertNotIn(private_table, improved)

    @patch('shop.llm.ask_llm')
    def test_ask_sql_validates_mock_output(self, ask):
        ask.return_value = '```sql\nSELECT COUNT(*) FROM shop_customer;\n```'
        self.assertEqual(ask_sql('Сколько клиентов?', 'baseline'),
                         'SELECT COUNT(*) FROM shop_customer LIMIT 100')
        ask.assert_called_once_with(build_system_prompt('baseline'), 'Сколько клиентов?')
        ask.return_value = 'SELECT * FROM auth_user'
        with self.assertRaises(UnsafeSQLError):
            ask_sql('Покажи пользователей')

    @patch.dict(os.environ, {'LLM_BASE_URL': 'http://localhost:11434/v1',
                             'LLM_API_KEY': 'ollama', 'LLM_MODEL': 'test-model'})
    @patch('shop.llm.OpenAI')
    def test_ask_llm_uses_configured_chat_api(self, openai):
        client = openai.return_value.__enter__.return_value
        create = client.chat.completions.create
        create.return_value.choices = [SimpleNamespace(message=SimpleNamespace(content=NO_ANSWER_SQL))]
        self.assertEqual(ask_llm('System', 'User'), NO_ANSWER_SQL)
        openai.assert_called_once_with(base_url='http://localhost:11434/v1',
                                       api_key='ollama', timeout=60.0, max_retries=0)
        create.assert_called_once_with(
            model='test-model', temperature=0,
            messages=[{'role': 'system', 'content': 'System'},
                      {'role': 'user', 'content': 'User'}],
        )
