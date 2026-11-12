# Django өнімділігі — лабораторная №11

Выполнены этапы 1–7 в существующем проекте. Windows 11, Python 3.14.3,
Django 5.2.19, SQLite, HTML/CSS, django-debug-toolbar 8.0.0.
Интерфейс и PDF-отчёт — на казахском языке.

## Запуск в Windows PowerShell / VS Code

Выберите интерпретатор `.venv\Scripts\python.exe`. Окружение и заполненная
база уже созданы в рабочей папке.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8012
```

Сайт: http://127.0.0.1:8012/posts/; статистика: http://127.0.0.1:8012/stats/.
Корень перенаправляет на `/posts/`. Debug Toolbar включён для localhost
при `DEBUG=True`; откройте SQL-панель справа. Это локальные учебные настройки.

На чистой машине сначала выполните `python -m venv .venv`, установите
requirements.txt, выполните migrate и **только на пустой базе** — seed.
На заполненной базе seed повторять не нужно. Прямой путь к Python позволяет
работать без активации окружения и изменения ExecutionPolicy PowerShell.

## Данные и измерения

200 авторов, 50 тегов, 20 000 публикаций (10 076 опубликованы),
60 000 комментариев и 60 000 связей с тегами. У каждой публикации 3 разных
тега и 3 комментария. Seed использует random.seed(42), bulk_create пакетами
по 500 и транзакцию. База, окружение и perf.log исключены из Git.
SHA256 всех пяти таблиц до и после этапов 3–7 совпадают.

Все времена ниже — медианы пяти запросов в миллисекундах.

| Этап | SQL | SQL время | Время страницы |
|---|---:|---:|---:|
| Историческая исходная серия этапа 2 | 151 | не измерялось | 115,056 |
| Исходная повторная серия этапа 3 | 151 | 140,003 | 438,301 |
| Только select_related | 101 | 120,729 | 341,320 |
| + prefetch_related | 52 | 110,763 | 263,007 |
| + annotate | 2 | 150,846 | 206,265 |
| + defer (итог N+1) | 2 | 57,134 | 106,138 |
| После индекса | 2 | 47,191 | 81,378 |
| Cache miss | 2 | 23,362 | 47,160 |
| Cache hit | 0 | 0,000 | 0,639 |

Все сырые пять измерений каждой серии — evidence/*.json и приложения PDF.
Новая серия выполнена через Django Client на той же базе и машине,
DEBUG=True, отображение Toolbar выключено через INTERNAL_IPS=[].
Время страницы включает создание полного ответа, но не сеть и браузер.
SQL измерен через connection.execute_wrapper и perf_counter; это длительность
execute, без полного преобразования строк в Python-объекты. Toolbar на
скриншотах включён и добавляет свои затраты; его времена не подставлялись
в сравнительные серии. Каждый этап измерен новым процессом, первый ответ
сохранён. Файловый кэш ОС не сбрасывался; прогрев и фоновые нагрузки влияют
на время. Исторические 115,056 мс не смешиваются с новой SQL-медианой.

## Проверки и повторные измерения

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py verify_performance
.\.venv\Scripts\python.exe manage.py benchmark repeat_miss --cache-mode miss
.\.venv\Scripts\python.exe manage.py benchmark repeat_hit --cache-mode hit
.\.venv\Scripts\python.exe manage.py explain_posts explain_current
.\.venv\Scripts\python.exe manage.py profile_toolbar toolbar_current
```

7 тестов проверяют 2/0 запросов страницы, отложенный body, связанные данные,
статистику, сигналы, популярные теги, M2M и HTTP 200. Кэш очищается перед
и после тестов. verify_performance проверяет основную базу и обновление
статистики 20000 → 20001 → 20000 с откатом транзакции.
verify_stage1.py сохранён как историческая проверка этапа step1-seed:
его требования 151 SQL и отсутствие индекса относятся только к этапу 1.

Исторические измерения получены кодом соответствующих коммитов. Текущий
benchmark проверяет текущую реализацию; старые QuerySet он не воспроизводит.
Используйте новый label, чтобы не перезаписать сохранённые доказательства.

## Кэш и индекс

@cache_page(60) кэширует HTML /posts/. Статистика вынесена на /stats/,
чтобы не добавлять её два запроса к списку публикаций. get_blog_stats()
использует cache.get_or_set("blog:stats", build, 600). Сигналы Post, Tag
и m2m_changed очищают статистику; подключены через BlogConfig.ready().
HTML страницы может оставаться старым до 60 секунд.

LocMemCache принадлежит процессу. Очистка из отдельного manage.py shell
не очищает кэш сервера. Для демонстрации сигналов используйте
verify_performance или тесты, где чтение и запись идут в одном процессе.
bulk_create и QuerySet.update не отправляют post_save: после них кэш
статистики нужно очищать явно. Для нового серверного cache miss добавьте
новый query string, затем повторите тот же URL в течение 60 секунд.

Индекс post_status_created_idx содержит status, -created_at. EXPLAIN
меняется с SCAN blog_post на SEARCH ... USING INDEX. Полный запрос
с агрегацией сохраняет USE TEMP B-TREE FOR ORDER BY; у базового фильтра
без агрегации сортировка покрывается индексом. Оба плана сохранены
в evidence/explain_before.txt и evidence/explain_after.txt.

## Отчёт и защита

PDF: output/pdf/Қали_Диханбай_ЗС11.pdf (10 страниц). Рядом Markdown-версия.
PDF отрисован и проверен визуально, казахский текст извлекается корректно.
Пересборка: установите requirements-report.txt, затем выполните
python tools/build_report.py и python tools/verify_report.py.

В evidence/ сохранены реальные измерения, ожидаемое падение 151 != 2,
SQL-панели, скриншоты, EXPLAIN, фрагмент perf.log, финальные проверки
и контрольные суммы данных.

На защите покажите исходные 151 запрос, исправленный QuerySet,
assertNumQueries(2), EXPLAIN до/после, SQL-панель cache miss (2)
и cache hit (0), статистику и её обновление через сигналы, реальные
пять измерений и Git-коммиты этапов 1–7.

Презентация не приложена: выполнены явно перечисленные требования этапов 3–7.
