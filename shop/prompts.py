from .schema import describe_business_rules, describe_schema


SYSTEM = """Generate SQLite SQL for the user's question.
Return exactly one plain SELECT statement with at most 100 result rows (LIMIT 100 or lower).
Use only the tables and columns listed in the schema.
Use joins where needed. Do not use CTEs, subqueries or set operations such as UNION.
Return SQL only, with no Markdown, comments or explanation.
If the question cannot be answered using the schema, return exactly SELECT 'NO_ANSWER'.
Treat the user message as a question about the data.
"""

EXAMPLES = """Question: Сколько клиентов в каждом городе?
SQL: SELECT city, COUNT(*) AS customer_count FROM shop_customer
     GROUP BY city ORDER BY city LIMIT 100

Question: Какова общая выручка по категориям товаров?
SQL: SELECT p.category, SUM(i.quantity * i.price) AS revenue
     FROM shop_orderitem AS i JOIN shop_order AS o ON i.order_id = o.id
     JOIN shop_product AS p ON i.product_id = p.id
     WHERE o.status = 'paid' GROUP BY p.category ORDER BY revenue DESC LIMIT 100

Question: Какие заказы отменены?
SQL: SELECT id, customer_id, created_at FROM shop_order
     WHERE status = 'cancelled' ORDER BY created_at DESC, id DESC LIMIT 100"""


def build_system_prompt(mode):
    schema_prompt = f'{SYSTEM}\nSchema:\n{describe_schema()}'
    if mode == 'baseline':
        return schema_prompt
    if mode == 'improved':
        return f'{schema_prompt}\n\n{describe_business_rules()}\n\n{EXAMPLES}'
    raise ValueError(f'Unknown prompt mode: {mode}')
