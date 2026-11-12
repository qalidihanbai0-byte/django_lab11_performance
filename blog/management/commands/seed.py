import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from blog.models import Author, Comment, Post, Tag


class Command(BaseCommand):
    help = 'Create the stage 1 dataset in an empty blog database.'

    @transaction.atomic
    def handle(self, *args, **options):
        if any(model.objects.exists() for model in (Author, Tag, Post, Comment)):
            raise CommandError('Blog tables must be empty. Existing data was not changed.')

        random.seed(42)
        batch_size = 500
        authors = Author.objects.bulk_create(
            [Author(name=f'Автор {i:03d}') for i in range(1, 201)],
            batch_size=batch_size,
        )
        tags = Tag.objects.bulk_create(
            [Tag(name=f'Тақырып {i:02d}') for i in range(1, 51)],
            batch_size=batch_size,
        )

        # Keep memory bounded as well as batching each SQL insert.
        for start in range(0, 20_000, batch_size):
            posts = Post.objects.bulk_create(
                [
                    Post(
                        author=random.choice(authors),
                        title=f'Жарияланым №{i + 1}',
                        body=f'Бұл №{i + 1} жарияланымның мәтіні. Django өнімділігін зерттейміз.',
                        status=random.choice([Post.Status.DRAFT, Post.Status.PUBLISHED]),
                    )
                    for i in range(start, start + batch_size)
                ],
                batch_size=batch_size,
            )
            relations = []
            comments = []
            for post in posts:
                relations.extend(
                    Post.tags.through(post_id=post.pk, tag_id=tag.pk)
                    for tag in random.sample(tags, 3)
                )
                comments.extend(
                    Comment(post_id=post.pk, text=f'{i + 1}-пікір: қызықты жарияланым!')
                    for i in range(3)
                )
            Post.tags.through.objects.bulk_create(relations, batch_size=batch_size)
            Comment.objects.bulk_create(comments, batch_size=batch_size)

        self.stdout.write(self.style.SUCCESS(
            'Created 200 authors, 50 tags, 20000 posts, 60000 post-tag links, 60000 comments.'
        ))
