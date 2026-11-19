import random
from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from shop.models import Customer, Order, OrderItem, Product


CITIES = ('Алматы', 'Астана', 'Шымкент', 'Қарағанды', 'Ақтөбе')
CATEGORIES = ('Электроника', 'Киім', 'Кітаптар', 'Спорт', 'Үй тауарлары')


class Command(BaseCommand):
    help = 'Populate empty shop tables with sample data.'

    @transaction.atomic
    def handle(self, *args, **options):
        if any(model.objects.exists() for model in (Customer, Product, Order, OrderItem)):
            self.stdout.write('Shop already contains data. Skipping seed.')
            return

        random.seed(42)
        customers = Customer.objects.bulk_create([
            Customer(name=f'Клиент {number:02d}', city=CITIES[(number - 1) % len(CITIES)])
            for number in range(1, 51)
        ])
        products = Product.objects.bulk_create([
            Product(
                name=f'{category} {number:02d}',
                category=category,
                price=Decimal(random.randint(50_000, 5_000_000)).scaleb(-2),
            )
            for category in CATEGORIES
            for number in range(1, 7)
        ])

        now = timezone.localtime()
        year, month_index = divmod(now.year * 12 + now.month - 1 - 3, 12)
        month = month_index + 1
        start = now.replace(year=year, month=month, day=min(now.day, monthrange(year, month)[1]))
        window_seconds = int((now - start).total_seconds())
        statuses = [Order.Status.PAID] * 350 + [Order.Status.NEW] * 100 + [Order.Status.CANCELLED] * 50
        random.shuffle(statuses)
        orders = Order.objects.bulk_create([
            Order(
                customer=random.choice(customers),
                created_at=now - timedelta(seconds=random.randint(0, window_seconds)),
                status=status,
            )
            for status in statuses
        ])

        items = [
            OrderItem(order=order, product=product, quantity=random.randint(1, 5), price=product.price)
            for order in orders
            for product in random.sample(products, random.randint(1, 5))
        ]
        OrderItem.objects.bulk_create(items)

        self.stdout.write(self.style.SUCCESS(
            f'Created {len(customers)} customers, {len(products)} products, '
            f'{len(orders)} orders and {len(items)} order items.'
        ))
