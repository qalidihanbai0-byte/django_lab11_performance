from django.core.cache import cache
from django.test import TestCase

from .models import Author, Comment, Post, Tag


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

    def test_post_list_two_queries(self):
        with self.assertNumQueries(2):
            response = self.client.get('/posts/', HTTP_HOST='localhost')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<article class="post">', count=50)
        self.assertNotContains(response, 'Hidden draft')
