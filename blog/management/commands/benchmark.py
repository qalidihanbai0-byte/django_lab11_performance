"""Five comparable local requests; keep toolbar overhead out of measurements."""
import json
import platform
import statistics
import time
from pathlib import Path

import django
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection
from django.test import Client, override_settings


class Command(BaseCommand):
    help = 'Measure five /posts/ responses and save raw SQL/page timings.'

    def add_arguments(self, parser):
        parser.add_argument('label')
        parser.add_argument('--cache-mode', choices=['off', 'miss', 'hit'], default='off')

    def handle(self, *args, **options):
        label = options['label']
        client = Client(HTTP_HOST='localhost')
        runs = []
        with override_settings(INTERNAL_IPS=[]):
            if options['cache_mode'] == 'hit':
                cache.clear()
                client.get('/posts/')
            for i in range(5):
                if options['cache_mode'] != 'hit':
                    cache.clear()
                sql_times = []

                def timer(execute, sql, params, many, context):
                    started = time.perf_counter()
                    try:
                        return execute(sql, params, many, context)
                    finally:
                        sql_times.append((time.perf_counter() - started) * 1000)

                started = time.perf_counter()
                with connection.execute_wrapper(timer):
                    response = client.get('/posts/')
                elapsed = (time.perf_counter() - started) * 1000
                assert response.status_code == 200
                assert response.content.count(b'<article class="post">') == 50
                run = {'run': i + 1, 'sql': len(sql_times),
                       'sql_ms': round(sum(sql_times), 6), 'page_ms': round(elapsed, 6)}
                runs.append(run)
                self.stdout.write(json.dumps(run))
        result = {'label': label, 'python': platform.python_version(),
                  'django': django.get_version(), 'database': 'same db.sqlite3',
                  'method': 'Django Client GET; DEBUG=True; toolbar hidden; no network; perf_counter SQL execute wrapper',
                  'cache_mode': options['cache_mode'], 'runs': runs,
                  'median_sql_ms': statistics.median(r['sql_ms'] for r in runs),
                  'median_page_ms': statistics.median(r['page_ms'] for r in runs)}
        folder = Path('evidence')
        folder.mkdir(exist_ok=True)
        (folder / f'{label}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        self.stdout.write(f"Median: SQL {result['median_sql_ms']:.3f} ms; page {result['median_page_ms']:.3f} ms")
