from django.shortcuts import render
from django.db.models import Count

from .models import Post


def posts_queryset():
    return (Post.objects
             .select_related("author")
             .prefetch_related("tags")
             .annotate(n_comments=Count("comments"))
             .defer("body")
             .filter(status="published")
             .order_by("-created_at")[:50])


def post_list(request):
    posts = posts_queryset()
    return render(request, 'blog/post_list.html', {'posts': posts})
