from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .models import Post, Tag


@receiver(post_save, sender=Post)
@receiver(post_delete, sender=Post)
@receiver(post_save, sender=Tag)
@receiver(post_delete, sender=Tag)
def invalidate_blog_stats(sender, **kwargs):
    cache.delete('blog:stats')


@receiver(m2m_changed, sender=Post.tags.through)
def invalidate_tag_counts(sender, action, **kwargs):
    if action in {'post_add', 'post_remove', 'post_clear'}:
        cache.delete('blog:stats')
