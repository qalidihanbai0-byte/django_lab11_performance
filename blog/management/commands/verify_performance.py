"""Check real data, page cache and signals without retaining any data changes."""
import json
from pathlib import Path

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext

from blog.models import Author, Comment, Post, Tag
from blog.stats import get_blog_stats
from blog.views import posts_queryset


class Command(BaseCommand):
    help = 'Verify final performance requirements on the seeded database.'

    def handle(self, *args, **options):
        counts = [m.objects.count() for m in (Author, Tag, Post, Comment, Post.tags.through)]
        assert counts == [200, 50, 20000, 60000, 60000], counts
        client = Client(HTTP_HOST='localhost')
        with override_settings(INTERNAL_IPS=[]):
            cache.clear()
            with CaptureQueriesContext(connection) as miss:
                first = client.get('/posts/')
            miss_count = len(miss)
            with CaptureQueriesContext(connection) as hit:
                second = client.get('/posts/')
            hit_count = len(hit)
            assert first.status_code == second.status_code == 200
            assert miss_count == 2 and hit_count == 0
            assert first.content == second.content
            assert first.content.count(b'<article class="post">') == 50
            cache.clear()
            with CaptureQueriesContext(connection) as stats_miss:
                stats = get_blog_stats()
            stats_miss_count = len(stats_miss)
            with CaptureQueriesContext(connection) as stats_hit:
                assert stats == get_blog_stats()
            stats_hit_count = len(stats_hit)
            assert stats_miss_count == 2 and stats_hit_count == 0
            assert stats['post_count'] == 20000 and len(stats['popular_tags']) == 10
            try:
                with transaction.atomic():
                    post = Post.objects.create(author_id=Author.objects.first().pk, title='Cache probe')
                    assert cache.get('blog:stats') is None
                    assert get_blog_stats()['post_count'] == 20001
                    post.delete()
                    assert cache.get('blog:stats') is None
                    assert get_blog_stats()['post_count'] == 20000
                    transaction.set_rollback(True)
            finally:
                cache.clear()
            assert client.get('/stats/').status_code == 200
        plan = posts_queryset().explain()
        assert 'post_status_created_idx' in plan
        result = {'counts': counts, 'page_miss_sql': miss_count, 'page_hit_sql': hit_count,
                  'stats_miss_sql': stats_miss_count, 'stats_hit_sql': stats_hit_count,
                  'stats_add_delete': '20000 -> 20001 -> 20000; rolled back',
                  'http_posts': 200, 'http_stats': 200, 'explain': plan,
                  'popular_tags': stats['popular_tags']}
        Path('evidence/final-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        self.stdout.write(json.dumps(result, indent=2))
