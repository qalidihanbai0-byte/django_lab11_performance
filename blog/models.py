from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Жоба'
        PUBLISHED = 'published', 'Жарияланған'

    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag)
    title = models.CharField(max_length=250)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at'], name='post_status_created_idx'),
        ]

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
