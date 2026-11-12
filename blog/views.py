from django.shortcuts import render
from django.db.models import Count
from django.views.decorators.cache import cache_page

from .models import Post
from .stats import get_blog_stats


def posts_queryset():
    return (Post.objects
             .select_related("author")
             .prefetch_related("tags")
             .annotate(n_comments=Count("comments"))
             .defer("body")
             .filter(status="published")
             .order_by("-created_at")[:50])


@cache_page(60)
def post_list(request):
    posts = posts_queryset()
    return render(request, 'blog/post_list.html', {'posts': posts})


def blog_stats(request):
    return render(request, 'blog/stats.html', {'stats': get_blog_stats()})
