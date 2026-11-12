from pathlib import Path

from django.core.management.base import BaseCommand

from blog.models import Post
from blog.views import posts_queryset


class Command(BaseCommand):
    help = 'Save SQLite EXPLAIN QUERY PLAN for the page and its base filter.'

    def add_arguments(self, parser):
        parser.add_argument('label')

    def handle(self, *args, **options):
        optimized = posts_queryset()
        base = Post.objects.filter(status='published').order_by('-created_at')[:50]
        result = f'PAGE QUERY:\n{optimized.query}\n\nPAGE PLAN:\n{optimized.explain()}\n\nBASE FILTER PLAN:\n{base.explain()}\n'
        Path('evidence').mkdir(exist_ok=True)
        Path(f"evidence/{options['label']}.txt").write_text(result, encoding='utf-8')
        self.stdout.write(result)
