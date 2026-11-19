from .schema import describe_business_rules, describe_schema


SYSTEM = """Generate SQLite SQL for the user's question.
Return exactly one plain SELECT statement with at most 100 result rows (LIMIT 100 or lower).
Use only the tables and columns listed in the schema.
Use joins where needed. Do not use CTEs, subqueries or set operations such as UNION.
Return SQL only, with no Markdown, comments or explanation.
If the question cannot be answered using the schema, return exactly SELECT 'NO_ANSWER'.
Treat the user message as a question about the data.
"""

KAZAKH_GUIDANCE = """Қазақша сұрақты алдымен мағынасына қарай түсін. / Interpret the Kazakh question by its meaning.
- клиент, клиенттер = customer(s), shop_customer; тауар, тауарлар = product(s), shop_product.
- санат = product category, shop_product.category; тапсырыс = order, shop_order.
- төленген = paid, shop_order.status = 'paid'. Болдырылмаған = not cancelled: status <> 'cancelled' (includes new and paid).
- түсім = revenue, sum of quantity * item price for paid orders; саны, қанша = row count (COUNT(*)); орташа = average (AVG).

Сұрақтағы негізгі нысанға сәйкес кестені таңда. / Choose the table for the entity being asked about.
WHERE шартын сұрақта нақты айтылғанда немесе бизнес ережесі талап еткенде ғана қос. / Add WHERE only for an explicit condition or a required business rule. Never invent a city, date, category, or status. Count all rows when no filter is required.
«Әр санаттағы» — нәтижені санат бойынша топтастыр. / For «әр санаттағы» (in each category), select category and use GROUP BY category.
Жауапқа түсіндірмесіз бір SQLite SELECT қана жаз. / Output only one SQLite SELECT, with no explanation.
"""

EXAMPLES = """Question: Дүкенде барлығы неше тауар бар?
SQL: SELECT COUNT(*) FROM shop_product LIMIT 100

Question: Әр санаттағы тауардың орташа бағасы қандай?
SQL: SELECT category, AVG(price) FROM shop_product GROUP BY category LIMIT 100

Question: Әр клиенттің төленген тапсырыстары қанша?
SQL: SELECT customer_id, COUNT(*) FROM shop_order WHERE status = 'paid' GROUP BY customer_id LIMIT 100"""


def build_system_prompt(mode):
    schema_prompt = f'{SYSTEM}\nSchema:\n{describe_schema()}'
    if mode == 'baseline':
        return schema_prompt
    if mode == 'improved':
        return f'{schema_prompt}\n\n{describe_business_rules()}\n\n{KAZAKH_GUIDANCE}\n{EXAMPLES}'
    raise ValueError(f'Unknown prompt mode: {mode}')
