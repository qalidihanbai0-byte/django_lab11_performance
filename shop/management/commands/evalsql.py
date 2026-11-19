import csv
import hashlib
import json
import os
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from openai import OpenAIError

from shop.guard import NO_ANSWER_SQL, UnsafeSQLError, extract_sql, run_readonly, validate_sql
from shop.llm import ask_llm
from shop.prompts import build_system_prompt


MODES = ('baseline', 'improved')
DEFAULT_MODEL = 'qwen2.5-coder:1.5b'


def comparable_rows(rows):
    # SQLite represents numbers as either INTEGER or REAL. Keep text and NULL
    # distinct and round fractional noise to six decimal places.
    return [
        tuple(
            Decimal(str(round(value, 6))) if isinstance(value, float) else value
            for value in row
        )
        for row in rows
    ]


def compare_results(expected, actual, ordered):
    expected_columns, expected_rows = expected
    actual_columns, actual_rows = actual
    # Column aliases are arbitrary. Compare positional values and row widths.
    width = len(expected_columns)
    if len(actual_columns) != width or any(len(row) != width for row in actual_rows):
        return 'column_structure'
    expected_values = comparable_rows(expected_rows)
    actual_values = comparable_rows(actual_rows)
    if Counter(expected_values) != Counter(actual_values):
        return 'result_mismatch'
    if ordered and expected_values != actual_values:
        return 'row_order'
    return ''


def evaluate_case(case, expected, mode, system):
    entry = {
        'id': case['id'], 'level': case['level'], 'question': case['question'],
        'mode': mode, 'ordered': case['ordered'], 'reference_sql': case['sql'],
        'reference_columns': expected[0], 'reference_rows': expected[1],
        'raw_response': None, 'sql': None, 'columns': None, 'rows': None,
        'error_type': '', 'error': '',
    }
    try:
        entry['raw_response'] = ask_llm(system, case['question'])
        entry['sql'] = validate_sql(extract_sql(entry['raw_response']))
        if entry['sql'] == NO_ANSWER_SQL:
            entry.update(error_type='no_answer', error='The model returned NO_ANSWER.')
        else:
            entry['columns'], entry['rows'] = run_readonly(entry['sql'])
            error_type = compare_results(expected, (entry['columns'], entry['rows']), case['ordered'])
            if error_type:
                entry.update(error_type=error_type, error='The result differs from the reference.')
    except UnsafeSQLError as exc:
        entry.update(error_type='guard_rejection', error=str(exc))
    except sqlite3.Error as exc:
        entry.update(error_type='sqlite_error', error=str(exc))
    except (OpenAIError, IndexError, OSError) as exc:
        entry.update(error_type='provider_error', error=type(exc).__name__)
    entry['correct'] = not entry['error_type']
    return entry


class Command(BaseCommand):
    help = 'Evaluate two prompt modes against the frozen golden.json reference questions.'

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true', help='Run reference SQL without Ollama.')

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR)
        source = (root / 'golden.json').read_bytes()
        cases = json.loads(source)
        if len(cases) != 10 or len({case['id'] for case in cases}) != 10:
            raise CommandError('Expected exactly 10 distinct reference questions.')
        references = []
        for case in cases:
            try:
                references.append(run_readonly(case['sql']))
            except (UnsafeSQLError, sqlite3.Error) as exc:
                raise CommandError(f"Invalid reference {case['id']}: {exc}") from exc

        checksum = hashlib.sha256(source).hexdigest()
        self.stdout.write(f'golden.json SHA-256 {checksum}')
        if options['verify_only']:
            for case, (columns, rows) in zip(cases, references, strict=True):
                self.stdout.write(f"{case['id']} {columns}: {rows}")
            return

        started = timezone.localtime().isoformat(timespec='seconds')
        systems = {mode: build_system_prompt(mode) for mode in MODES}
        results = []
        for case, expected in zip(cases, references, strict=True):
            for mode, system in systems.items():
                entry = evaluate_case(case, expected, mode, system)
                results.append(entry)
                self.stdout.write(f"{case['id']}  {mode:8}  {entry['error_type'] or 'correct'}")

        summary = {
            'model': os.getenv('LLM_MODEL', DEFAULT_MODEL),
            'experiment_at': started, 'question_count': len(cases),
            'call_attempts': len(results), 'golden_sha256': checksum,
            'prompt_sha256': {key: hashlib.sha256(value.encode()).hexdigest()
                              for key, value in systems.items()},
            'modes': {},
        }
        for mode in MODES:
            entries = [entry for entry in results if entry['mode'] == mode]
            correct = sum(entry['correct'] for entry in entries)
            summary['modes'][mode] = {
                'correct': correct, 'incorrect': len(entries) - correct,
                'accuracy_percent': 100 * correct / len(entries),
                'error_types': dict(Counter(entry['error_type'] for entry in entries if not entry['correct'])),
            }
        baseline, improved = (summary['modes'][mode]['accuracy_percent'] for mode in MODES)
        summary['difference_percentage_points'] = improved - baseline

        output = root / 'evaluation'
        output.mkdir(exist_ok=True)
        for name, data in (('results', results), ('summary', summary)):
            (output / f'{name}.json').write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
            )
        with (output / 'results.csv').open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(results[0]))
            writer.writeheader()
            for entry in results:
                writer.writerow({
                    key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, tuple)) else value
                    for key, value in entry.items()
                })

        self.stdout.write('Mode      Correct  Incorrect  Accuracy')
        for mode, stats in summary['modes'].items():
            self.stdout.write(
                f"{mode:8}  {stats['correct']:7}  {stats['incorrect']:9}  {stats['accuracy_percent']:7.1f}%"
            )
