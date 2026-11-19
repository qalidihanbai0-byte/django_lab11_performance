import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase

from shop.management.commands.evalsql import compare_results


class ResultComparisonTests(SimpleTestCase):
    def test_numeric_types_null_duplicates_and_order(self):
        expected = (['n', 'label'], [(1, None), (2, 'a'), (2, 'a')])
        actual = (['number', 'name'], [(2.0, 'a'), (1.0, None), (2, 'a')])
        self.assertEqual(compare_results(expected, actual, ordered=False), '')
        self.assertEqual(compare_results(expected, actual, ordered=True), 'row_order')
        self.assertEqual(compare_results(expected, (actual[0], actual[1][:-1]), False), 'result_mismatch')
        self.assertEqual(compare_results((['n'], [(None,)]), (['x'], [('NULL',)]), False), 'result_mismatch')

    def test_column_structure_is_checked_even_without_rows(self):
        self.assertEqual(compare_results((['a'], []), (['a', 'b'], []), False), 'column_structure')
        self.assertEqual(compare_results((['a'], [(1,)]), (['a'], [(1, 2)]), False), 'column_structure')


class EvalSQLCommandTests(SimpleTestCase):
    @patch('shop.management.commands.evalsql.run_readonly', return_value=(['n'], [(1,)]))
    @patch('shop.management.commands.evalsql.ask_llm')
    def test_records_both_modes_and_preserves_raw_rejections(self, ask, run):
        ask.side_effect = ['SELECT 1', 'DELETE FROM shop_order'] * 10
        golden = (Path(settings.BASE_DIR) / 'golden.json').read_bytes()
        with TemporaryDirectory() as workspace, self.settings(BASE_DIR=Path(workspace)):
            root = Path(workspace)
            (root / 'golden.json').write_bytes(golden)
            call_command('evalsql', stdout=StringIO())
            output = root / 'evaluation'
            results = json.loads((output / 'results.json').read_text(encoding='utf-8'))
            summary = json.loads((output / 'summary.json').read_text(encoding='utf-8'))
            self.assertTrue((output / 'results.csv').is_file())

        self.assertEqual(ask.call_count, 20)
        self.assertEqual(run.call_count, 20)
        self.assertEqual(len(results), 20)
        self.assertEqual(results[1]['raw_response'], 'DELETE FROM shop_order')
        self.assertEqual(results[1]['error_type'], 'guard_rejection')
        self.assertEqual(summary['modes']['baseline']['accuracy_percent'], 100.0)
        self.assertEqual(summary['modes']['improved']['accuracy_percent'], 0.0)
