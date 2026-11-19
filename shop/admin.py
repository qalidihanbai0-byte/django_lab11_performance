from django.contrib import admin

from .models import Customer, Order, OrderItem, Product, QueryLog


admin.site.register([Customer, Product, Order, OrderItem])


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ('question', 'sql', 'error', 'created_at')
    search_fields = ('question',)
    ordering = ('-created_at',)
