"""Verify the seeded stage 1 database without changing it."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_lab11_performance.settings')
django.setup()
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from blog.models import Author, Tag, Post, Comment

counts = [model.objects.count() for model in (Author, Tag, Post, Comment, Post.tags.through)]
assert counts == [200, 50, 20000, 60000, 60000], counts
print('Counts (authors, tags, posts, comments, post_tags):', counts)
print('Published:', Post.objects.filter(status='published').count())
with connection.cursor() as cursor:
    for table in ('blog_post_tags', 'blog_comment'):
        cursor.execute(f'SELECT COUNT(*) FROM (SELECT post_id FROM {table} GROUP BY post_id HAVING COUNT(*) != 3)')
        assert cursor.fetchone()[0] == 0
    cursor.execute("PRAGMA index_list('blog_post')")
    indexes = cursor.fetchall()
    for index in indexes:
        cursor.execute('PRAGMA index_info("' + index[1] + '")')
        fields = [row[2] for row in cursor.fetchall()]
        assert 'status' not in fields and 'created_at' not in fields
    print('Post indexes:', indexes)
client = Client(HTTP_HOST='localhost')
with CaptureQueriesContext(connection) as queries:
    response = client.get('/posts/')
assert response.status_code == 200
html = response.content.decode()
assert html.count('<article class="post">') == 50
assert len(queries) == 151, len(queries)
expected = list(Post.objects.filter(status='published').order_by('-created_at')[:50])
positions = [html.index('<h2>' + p.title + '</h2>') for p in expected]
assert positions == sorted(positions)
assert '<html lang="kk">' in html
assert client.get('/').status_code == 302
print('PASS: HTTP 200, 50 latest published posts, Kazakh HTML, 151 SQL queries')
print('PASS: exactly 3 tags and 3 comments per post; no status/created_at indexes')
