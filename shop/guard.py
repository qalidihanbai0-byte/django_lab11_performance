import re
import sqlite3
from contextlib import closing
from pathlib import Path
from time import monotonic

import sqlglot
from django.conf import settings
from sqlglot import exp
from sqlglot.errors import ErrorLevel, SqlglotError
from sqlglot.optimizer.qualify import qualify

from .schema import allowed_schema


MAX_ROWS = 100
MAX_SQL_LENGTH = 8_000
QUERY_TIMEOUT_SECONDS = 2.0
NO_ANSWER_SQL = "SELECT 'NO_ANSWER'"
MARKDOWN_SQL = re.compile(r'```(?:sql|sqlite)?[^\S\r\n]*\r?\n(.*?)\r?\n```', re.I | re.S)

# A flat SELECT is sufficient for the supported reports. Every AST node must
# be recognized before SQLGlot renders the query for SQLite.
ALLOWED_EXPRESSIONS = {
    exp.Select, exp.From, exp.Join, exp.Table, exp.TableAlias, exp.Alias,
    exp.Identifier, exp.Column, exp.Star, exp.Literal, exp.Null, exp.Boolean,
    exp.Where, exp.Group, exp.Having, exp.Order, exp.Ordered, exp.Limit,
    exp.Distinct, exp.Paren, exp.And, exp.Or, exp.Not, exp.Is,
    exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE, exp.Between, exp.In, exp.Like,
    exp.Add, exp.Sub, exp.Mul, exp.Div, exp.Mod, exp.Neg,
    exp.Count, exp.Sum, exp.Avg, exp.Min, exp.Max, exp.Round, exp.Coalesce,
    exp.Lower, exp.Upper, exp.Date, exp.TimeToStr, exp.TsOrDsToTimestamp,
}
SQLITE_FUNCTIONS = {
    'count', 'sum', 'avg', 'min', 'max', 'round', 'coalesce', 'lower',
    'upper', 'date', 'strftime', 'like',
}


class UnsafeSQLError(ValueError):
    """The query is outside the supported read-only report dialect."""


def extract_sql(response):
    if not isinstance(response, str) or not response.strip():
        raise UnsafeSQLError('Expected a nonempty SQL response.')
    sql = response.strip()
    if len(sql) > MAX_SQL_LENGTH:
        raise UnsafeSQLError('SQL response is too long.')
    fenced = MARKDOWN_SQL.fullmatch(sql)
    if fenced:
        sql = fenced[1].strip()
    if not sql:
        raise UnsafeSQLError('Expected a nonempty SQL response.')
    return sql


def validate_sql(sql):
    """Return a validated SQLite SELECT with an enforced result limit."""
    if not isinstance(sql, str) or not sql.strip() or len(sql) > MAX_SQL_LENGTH or '\x00' in sql:
        raise UnsafeSQLError('Expected one nonempty SELECT statement within the size limit.')

    try:
        statements = sqlglot.parse(sql, read='sqlite')
        if len(statements) != 1 or type(statements[0]) is not exp.Select:
            raise UnsafeSQLError('Only one SELECT statement is allowed.')
        query = statements[0]
        for node in query.walk():
            if node.comments or type(node) not in ALLOWED_EXPRESSIONS:
                raise UnsafeSQLError('Unsupported SQL syntax.')
            if node is not query and isinstance(node, exp.Select):
                raise UnsafeSQLError('Nested SELECT statements are forbidden.')

        schema = allowed_schema()
        for table in query.find_all(exp.Table):
            if (
                not isinstance(table.this, exp.Identifier)
                or table.db or table.catalog or table.name.lower() not in schema
            ):
                raise UnsafeSQLError('Table is outside the reporting schema.')

        if query.sql(dialect='sqlite') == NO_ANSWER_SQL:
            return NO_ANSWER_SQL

        # Resolve columns and aliases against the model metadata without
        # opening the database or rewriting the query with optimizer rules.
        qualify(
            query.copy(), dialect='sqlite',
            schema={table: dict.fromkeys(columns, 'UNKNOWN') for table, columns in schema.items()},
        )

        limit = query.args.get('limit')
        row_count = MAX_ROWS
        if limit is not None:
            count = limit.expression
            if not isinstance(count, exp.Literal) or not count.is_int or int(count.this) < 0:
                raise UnsafeSQLError('LIMIT must be a nonnegative integer.')
            row_count = min(int(count.this), MAX_ROWS)
        return query.limit(row_count, copy=False).sql(dialect='sqlite', unsupported_level=ErrorLevel.RAISE)
    except UnsafeSQLError:
        raise
    except (SqlglotError, RecursionError, ValueError) as exc:
        raise UnsafeSQLError('Invalid or unsupported SQLite query.') from exc


def run_readonly(sql):
    """Return column names and rows, or two empty lists for NO_ANSWER."""
    sql = validate_sql(sql)
    if sql == NO_ANSWER_SQL:
        return [], []

    schema = allowed_schema()

    def authorize(action, first, second, database, source):
        if source is None:
            if action == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and (second or '').lower() in SQLITE_FUNCTIONS:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_READ and database in ('main', None):
                columns = schema.get((first or '').lower())
                # SQLite reports an empty column for table-only reads such as COUNT(*).
                if columns is not None and (second == '' or (second or '').lower() in columns):
                    return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    db_path = Path(settings.DATABASES['default']['NAME']).resolve()
    deadline = monotonic() + QUERY_TIMEOUT_SECONDS
    with closing(sqlite3.connect(f'{db_path.as_uri()}?mode=ro', uri=True, timeout=QUERY_TIMEOUT_SECONDS)) as db:
        db.execute('PRAGMA query_only=ON')
        db.set_authorizer(authorize)
        db.set_progress_handler(lambda: monotonic() >= deadline, 1_000)
        cursor = db.execute(sql)
        return [column[0] for column in cursor.description], cursor.fetchmany(MAX_ROWS)
