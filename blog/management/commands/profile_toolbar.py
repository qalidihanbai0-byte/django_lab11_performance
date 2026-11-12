import json
from pathlib import Path
from unittest.mock import patch

from debug_toolbar.panels.sql.panel import SQLPanel
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.test import Client, override_settings


class Command(BaseCommand):
    help = 'Verify and save real Django Debug Toolbar SQL panel output.'

    def add_arguments(self, parser):
        parser.add_argument('label')

    def handle(self, *args, **options):
        measured = {}
        original = SQLPanel.generate_stats

        def capture(panel, request, response):
            original(panel, request, response)
            stats = panel.get_stats()
            measured.update(sql=len(stats['queries']), sql_ms=stats['sql_time'],
                            queries=[q['sql'] for q in stats['queries']])

        cache.clear()
        with override_settings(DEBUG=True, DEBUG_TOOLBAR_CONFIG={
            'RENDER_PANELS': True, 'IS_RUNNING_TESTS': False,
        }), patch.object(SQLPanel, 'generate_stats', capture):
            response = Client(HTTP_HOST='localhost').get('/posts/', REMOTE_ADDR='127.0.0.1')
        assert response.status_code == 200
        assert b'djDebug' in response.content and b'SQLPanel' in response.content
        assert measured
        folder = Path('evidence')
        folder.mkdir(exist_ok=True)
        (folder / f"{options['label']}.json").write_text(json.dumps(measured, indent=2), encoding='utf-8')
        (folder / f"{options['label']}.html").write_bytes(response.content)
        self.stdout.write(f"SQL panel: {measured['sql']} queries, {measured['sql_ms']:.3f} ms; HTTP 200")
