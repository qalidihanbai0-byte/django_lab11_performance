from django.core.cache import cache
from django.db.models import Count

from .models import Post, Tag


def get_blog_stats():
    def build():
        return {
            'post_count': Post.objects.count(),
            'popular_tags': list(
                Tag.objects.annotate(n_posts=Count('post'))
                .order_by('-n_posts', 'pk')
                .values('name', 'n_posts')[:10]
            ),
        }

    return cache.get_or_set('blog:stats', build, 600)
