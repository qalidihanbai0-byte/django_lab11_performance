from django.contrib import admin

from .models import Customer, Order, OrderItem, Product, QueryLog


admin.site.register([Customer, Product, Order, OrderItem, QueryLog])
