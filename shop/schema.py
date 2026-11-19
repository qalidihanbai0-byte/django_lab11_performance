from .models import Customer, Order, OrderItem, Product


REPORT_MODELS = (Customer, Product, Order, OrderItem)


def allowed_schema():
    return {
        model._meta.db_table: {field.column: field.get_internal_type()
                               for field in model._meta.concrete_fields}
        for model in REPORT_MODELS
    }


def describe_schema():
    lines = []
    schema = allowed_schema()
    for model in REPORT_MODELS:
        table = model._meta.db_table
        columns = schema[table]
        fields = ', '.join(f'{column} ({kind})' for column, kind in columns.items())
        lines.append(f'{table}: {fields}')
        for field in model._meta.concrete_fields:
            if field.many_to_one:
                target = field.target_field
                lines.append(f'  FK {table}.{field.column} -> '
                             f'{target.model._meta.db_table}.{target.column}')
    return '\n'.join(lines)


def describe_business_rules():
    order = Order._meta
    item = OrderItem._meta
    statuses = ', '.join(Order.Status.values)
    return (
        f'Order statuses: {statuses}. A sale only includes orders where '
        f"{order.db_table}.{order.get_field('status').column} = '{Order.Status.PAID}'.\n"
        f"Revenue per item = {item.db_table}.{item.get_field('quantity').column} * "
        f"{item.db_table}.{item.get_field('price').column}. Prices are in Kazakhstani tenge (KZT)."
    )
