from django.core.cache import cache
from django.test import TestCase

from .models import Author, Comment, Post, Tag
from .stats import get_blog_stats


class PostListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        author = Author.objects.create(name='Test author')
        tags = Tag.objects.bulk_create([Tag(name=f'Tag {i}') for i in range(3)])
        for i in range(50):
            post = Post.objects.create(author=author, title=f'Post {i}', body='Body', status='published')
            post.tags.add(*tags)
            Comment.objects.create(post=post, text='Comment')
        Post.objects.create(author=author, title='Hidden draft', body='Draft')

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_post_list_two_queries(self):
        with self.assertNumQueries(2):
            response = self.client.get('/posts/', HTTP_HOST='localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<article class="post">', count=50)
        self.assertNotContains(response, 'Hidden draft')

    def test_page_cache_hit_has_no_queries(self):
        with self.assertNumQueries(2):
            first = self.client.get('/posts/', HTTP_HOST='localhost')
        with self.assertNumQueries(0):
            second = self.client.get('/posts/', HTTP_HOST='localhost')
        self.assertEqual(first.content, second.content)

    def test_optimized_objects_keep_body_deferred(self):
        from .views import posts_queryset
        with self.assertNumQueries(2):
            posts = list(posts_queryset())
        self.assertEqual(len(posts), 50)
        for post in posts:
            self.assertIn('body', post.get_deferred_fields())
            with self.assertNumQueries(0):
                self.assertEqual(post.n_comments, 1)
                self.assertEqual(post.author.name, 'Test author')
                self.assertEqual(len(post.tags.all()), 3)


class BlogStatsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.author = Author.objects.create(name='Author')
        self.tag = Tag.objects.create(name='Tag')

    def tearDown(self):
        cache.clear()

    def test_stats_miss_and_hit(self):
        with self.assertNumQueries(2):
            first = get_blog_stats()
        with self.assertNumQueries(0):
            second = get_blog_stats()
        self.assertEqual(first, second)
        self.assertEqual(first['post_count'], 0)

    def test_post_save_update_and_delete_invalidate_stats(self):
        self.assertEqual(get_blog_stats()['post_count'], 0)
        post = Post.objects.create(author=self.author, title='New')
        self.assertIsNone(cache.get('blog:stats'))
        self.assertEqual(get_blog_stats()['post_count'], 1)
        post.title = 'Updated'
        post.save()
        self.assertIsNone(cache.get('blog:stats'))
        self.assertEqual(get_blog_stats()['post_count'], 1)
        post.delete()
        self.assertIsNone(cache.get('blog:stats'))
        self.assertEqual(get_blog_stats()['post_count'], 0)

    def test_tag_relations_and_top_ten(self):
        tags = Tag.objects.bulk_create([Tag(name=f'Tag {i}') for i in range(12)])
        post = Post.objects.create(author=self.author, title='Post')
        get_blog_stats()
        post.tags.add(tags[-1])
        self.assertIsNone(cache.get('blog:stats'))
        stats = get_blog_stats()
        self.assertEqual(len(stats['popular_tags']), 10)
        self.assertEqual(stats['popular_tags'][0], {'name': tags[-1].name, 'n_posts': 1})
        post.tags.remove(tags[-1])
        self.assertIsNone(cache.get('blog:stats'))
        self.assertEqual(get_blog_stats()['popular_tags'][0]['n_posts'], 0)

    def test_stats_endpoint(self):
        with self.assertNumQueries(2):
            response = self.client.get('/stats/', HTTP_HOST='localhost')
        self.assertEqual(response.status_code, 200)
        with self.assertNumQueries(0):
            response = self.client.get('/stats/', HTTP_HOST='localhost')
        self.assertEqual(response.status_code, 200)
