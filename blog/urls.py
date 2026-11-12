from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'blog'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='blog:posts', permanent=False)),
    path('posts/', views.post_list, name='posts'),
]
