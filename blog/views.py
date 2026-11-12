from django.shortcuts import render

from .models import Post


def post_list(request):
    # Stage 1 baseline: intentionally retain the N+1 queries.
    posts = (Post.objects
             .filter(status="published")
             .order_by("-created_at")[:50])
    return render(request, 'blog/post_list.html', {'posts': posts})
