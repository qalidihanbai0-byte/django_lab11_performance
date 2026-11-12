"""Build the Kazakh lab report from measured JSON evidence, never invented values."""
from pathlib import Path
import json
import textwrap
import sys
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    Preformatted, Image,
)

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8')
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialBold', 'C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='ArialBold', italic='Arial', boldItalic='ArialBold')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyKK', fontName='Arial', fontSize=10, leading=14, spaceAfter=9))
styles.add(ParagraphStyle(name='TitleKK', fontName='ArialBold', fontSize=22, leading=28, spaceAfter=16))
styles.add(ParagraphStyle(name='HeadingKK', fontName='ArialBold', fontSize=15, leading=20, spaceAfter=12))
styles.add(ParagraphStyle(name='SmallKK', fontName='Arial', fontSize=8, leading=11, spaceAfter=7))
styles.add(ParagraphStyle(name='CellKK', fontName='Arial', fontSize=8.4, leading=11))
styles.add(ParagraphStyle(name='CodeKK', fontName='Arial', fontSize=7.5, leading=10,
                         backColor=colors.HexColor('#f0f3f6'), borderPadding=8, spaceAfter=12))
story, markdown = [], []


def p(text, small=False):
    story.append(Paragraph(escape(text), styles['SmallKK' if small else 'BodyKK']))
    markdown.append(text + '\n')


def h(text, title=False):
    story.append(Paragraph(escape(text), styles['TitleKK' if title else 'HeadingKK']))
    markdown.append(('# ' if title else '## ') + text + '\n')


def code(text):
    wrapped = '\n'.join('\n'.join(textwrap.wrap(line, width=100, break_long_words=True, replace_whitespace=False)) if line else '' for line in text.splitlines())
    story.append(Preformatted(escape(wrapped), styles['CodeKK']))
    markdown.append('```text\n' + text + '\n```\n')


def table(headers, rows, widths, compact=False):
    cells = [[Paragraph(escape(str(value)), styles['CellKK']) for value in row] for row in [headers] + rows]
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2efed')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#bdcbd2')),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 3 if compact else 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3 if compact else 6),
    ]))
    story.extend([t, Spacer(1, 12)])
    markdown.append('| ' + ' | '.join(headers) + ' |\n| ' + ' | '.join(['---'] * len(headers)) + ' |\n' + '\n'.join('| ' + ' | '.join(map(str, row)) + ' |' for row in rows) + '\n')


def picture(name, caption, width=470):
    image = Image(str(ROOT / 'evidence' / name))
    image.drawHeight = image.imageHeight * width / image.imageWidth
    image.drawWidth = width
    story.append(image)
    p(caption, small=True)
    markdown.append(f'![{caption}](../../evidence/{name})\n')


def page():
    story.append(PageBreak())


def number(value):
    return f'{value:.3f}'.replace('.', ',')


labels = ['baseline', 'select_related', 'prefetch_related', 'annotate', 'nplus1', 'index', 'cache_miss', 'cache_hit']
data = {label: json.loads((ROOT / f'evidence/{label}.json').read_text(encoding='utf-8')) for label in labels}
names = {
    'baseline': 'Бастапқы нұсқа (қайта өлшеу)', 'select_related': 'Авторды select_related арқылы алу',
    'prefetch_related': 'Тегтерге prefetch_related қосу', 'annotate': 'Пікір санын annotate арқылы алу',
    'nplus1': 'N+1 түзетілген, body кейінге қалдырылған', 'index': 'Құрама индекс қосылған',
    'cache_miss': 'Кэште жоқ жауап', 'cache_hit': 'Кэште бар жауап',
}

h('№11 зертханалық жұмыс\nDjango өнімділігі', title=True)
p('Орындаған: Қали Диханбай. Күні: 12.11.2026.')
h('Тақырыбы және мақсаты')
p('Django блогының өнімділігін өлшеу, N+1 мәселесін анықтау, байланысты деректерді тиімді алу, SQL орындалу жоспарын талдау және кэштеудің әсерін тәжірибе арқылы тексеру.')
h('Жобаның сипаттамасы және деректер саны')
p('Жоба: django_lab11_performance. Орта: Windows 11, VS Code, Python 3.14.3, Django 5.2.19, SQLite, HTML және CSS. /posts/ беті соңғы жарияланған 50 жазбаны көрсетеді. /stats/ бетінде блог статистикасы берілген.')
table(['Нысан', 'Саны'], [['Автор', '200'], ['Тақырып', '50'], ['Жарияланым', '20 000 (жарияланғаны 10 076)'], ['Пікір', '60 000'], ['Жарияланым-тақырып байланысы', '60 000; әр жазбада 3 тақырып']], [260, 245])
p('Деректер random.seed(42) және bulk_create арқылы жасалған. Барлық өлшеу бір компьютердегі бір SQLite базасында орындалды. Жұмыс соңында бес кестенің SHA256 бақылау сомалары бастапқы мәндерімен бірдей болды.', small=True)
picture('posts.png', '1-сурет. Оңтайландырылған жарияланымдар беті.', width=345)

page()
h('LOGGING және perf.log')
p('TimingMiddleware time.perf_counter() арқылы уақытты өлшейді, CaptureQueriesContext(connection) арқылы SQL санын есептейді. logging.getLogger("perf") әдісі сұрау әдісін, URL, миллисекундпен уақытты және SQL санын perf.log файлына жазады. 300 мс-тан жоғары уақыт WARNING, қалғаны INFO деңгейімен тіркеледі. Файл Git құрамына кірмейді.')
code('GET /posts/ duration_ms=44.773 sql_queries=2\nGET /posts/ duration_ms=0.592 sql_queries=0')
p('Бұл екі жол нақты журналдан алынды; олар бес өлшемдік салыстырмалы серияның орнына қолданылмайды.', small=True)
h('Django Debug Toolbar')
p('django-debug-toolbar 8.0.0 орнатылды. INSTALLED_APPS, MIDDLEWARE, INTERNAL_IPS және /__debug__/ маршруттары бапталды. SQL панелін тікелей тексеру бастапқы нұсқада 151 сұрауды көрсетті. Панельдің нақты өлшемі: 157,704 мс SQL уақыты; браузер суреті бөлек сұраудан алынған.')
picture('step3-sql.png', '2-сурет. SQL панелі: 151 сұрау және қайталанатын байланысты сұраулар.', width=480)
p('PostListTests тестіндегі assertNumQueries(2) оңтайландыруға дейін әдейі орындалмады: 151 != 2. Нақты хаттама evidence/step3-expected-failure.txt файлында сақталған.')

page()
h('N+1 мәселесін шешу')
p('Бастапқы бетте негізгі сұрауға қоса 50 автор, 50 тақырып тізімі және 50 пікір саны жеке сұралды: 1 + 50 + 50 + 50 = 151. Өзгерістер ретімен енгізіліп, әрқайсысынан кейін бес рет өлшенді.')
rows = []
for label in labels[:5]:
    d = data[label]
    rows.append([names[label], str(d['runs'][0]['sql']), number(d['median_sql_ms']), number(d['median_page_ms'])])
table(['Өзгеріс', 'SQL саны', 'SQL медианасы, мс', 'Бет медианасы, мс'], rows, [235, 55, 105, 110])
code('def posts_queryset():\n    return (Post.objects\n        .select_related("author")\n        .prefetch_related("tags")\n        .annotate(n_comments=Count("comments"))\n        .defer("body")\n        .filter(status="published")\n        .order_by("-created_at")[:50])\n\nШаблон: {{ p.n_comments }}')
p('select_related авторды JOIN арқылы алды. prefetch_related барлық көрсетілетін жазбалардың тақырыптарын екінші сұрауда алды. annotate әр жазбаның пікір санын негізгі сұрауда есептеді. defer бетте көрсетілмейтін body өрісін жүктемеді.')
p('Сұраулар саны нақты 151 → 101 → 52 → 2 → 2 болды. Сан азайғанымен, агрегацияның өзіндік құны бар: сондықтан SQL уақытын және толық жауап уақытын бөлек салыстыру қажет. assertNumQueries(2) тесті оңтайландырудан кейін өтті.')

page()
h('EXPLAIN нәтижелері және индекс')
p('SQLite жүйесінде QuerySet.explain() EXPLAIN QUERY PLAN нәтижесін береді. Алдымен индекске дейінгі жоспар сақталды, содан кейін Post.Meta.indexes арқылы құрама индекс қосылып, миграция қолданылды.')
code('models.Index(\n    fields=["status", "-created_at"],\n    name="post_status_created_idx",\n)\n\npython manage.py makemigrations blog\npython manage.py migrate')
h('Индекске дейінгі нақты жоспар')
before = (ROOT / 'evidence/explain_before.txt').read_text(encoding='utf-8').split('PAGE PLAN:\n')[1].split('\n\nBASE FILTER PLAN:')[0]
code(before)
h('Индекстен кейінгі нақты жоспар')
after = (ROOT / 'evidence/explain_after.txt').read_text(encoding='utf-8').split('PAGE PLAN:\n')[1].split('\n\nBASE FILTER PLAN:')[0]
code(after)
p('Негізгі өзгеріс: SCAN blog_post орнына SEARCH blog_post USING INDEX post_status_created_idx (status=?) қолданылды. Агрегациясы бар толық сұрауда USE TEMP B-TREE FOR ORDER BY сақталды. Тек status сүзгісі мен created_at сұрыптауы бар базалық сұрауда уақытша сұрыптау жойылды. Толық SQL және екі базалық жоспар evidence/explain_before.txt және evidence/explain_after.txt файлдарында бар.')
table(['Күйі', 'SQL саны', 'SQL медианасы, мс', 'Бет медианасы, мс'], [[name, 2, number(data[key]['median_sql_ms']), number(data[key]['median_page_ms'])] for name, key in [('Индекске дейін', 'nplus1'), ('Индекстен кейін', 'index')]], [200, 65, 120, 120])

page()
h('Кэштеу және статистиканы жаңарту')
p('LocMemCache бір Python процесінің жадында жұмыс істейді. /posts/ бетіне @cache_page(60) қосылды. Статистика бөлек /stats/ бетінде көрсетіледі: барлық жарияланым саны және ең танымал 10 тақырып. Осылайша /posts/ бетіндегі екі сұраулық тест статистика сұрауларымен араласпайды.')
code('cache.get_or_set("blog:stats", build, 600)\n\n@cache_page(60)\ndef post_list(request):\n    ...')
p('Статистика кэшінің жарамдылық мерзімі 600 секунд. Post үшін post_save және post_delete сигналдары blog:stats кілтін жояды; сигналдар BlogConfig.ready() ішінде қосылады. Тақырып өзгергенде және M2M байланыстары өзгергенде де статистика тазартылады.')
p('Нақты тексеру: статистиканың алғашқы оқылуы 2 SQL, қайталанған оқылуы 0 SQL. Жарияланым қосылғанда және жойылғанда сан 20000 → 20001 → 20000 болып жаңарды. Тексеру транзакциясы кері қайтарылып, бастапқы деректер сақталды.')
p('Әр тест алдында және соңында кэш тазартылады. Беттің кэште болмауы мен кэштен табылуы бөлек тексерілді. Статистика бірден жаңарады, ал дайын /posts/ HTML жауабы 60 секундқа дейін ескі болуы мүмкін. LocMemCache бірнеше сервер процесі арасында ортақ емес; bulk_create және QuerySet.update post_save сигналын жібермейді.', small=True)
picture('stats.png', '3-сурет. 20 000 жарияланым және ең танымал 10 тақырып.', width=460)

page()
h('Нәтижелер кестесі')
p('2-кезеңде бұрын алынған бес уақыт: 169,443; 117,866; 98,133; 99,733; 115,056 мс. Олардың медианасы 115,056 мс, SQL саны 151. Сол серияда SQL орындалу уақыты бөлек өлшенбеген, сондықтан ол үшін жаңа мән ойдан қосылған жоқ.')
summary = [['Бастапқы (2-кезеңдегі жазба)', '151', 'Өлшенбеген', '115,056']]
for label in ['baseline', 'nplus1', 'index', 'cache_miss', 'cache_hit']:
    d = data[label]
    summary.append([names[label], d['runs'][0]['sql'], number(d['median_sql_ms']), number(d['median_page_ms'])])
table(['Кезең', 'SQL саны', 'SQL уақыты, мс', 'Бет уақыты, мс'], summary, [235, 55, 105, 110])
h('Өлшеу әдісі және шектеулер')
p('Жаңа сериялардың әрқайсысында Django Client арқылы /posts/ бетіне бес GET сұрауы жіберілді. DEBUG=True сақталды, Toolbar көрсетуі INTERNAL_IPS=[] арқылы өшірілді. Бет уақыты time.perf_counter() арқылы толық жауап жасалғанша өлшенді; желі, браузердің сурет салуы және статикалық файлдар бұл уақытқа кірмейді.')
p('SQL уақыты connection.execute_wrapper арқылы әр SQL execute әрекетінің нақты ұзақтығын қосумен есептелді. Бұл барлық жолдарды Python объектісіне айналдыру уақытын толық қамтымайды және Toolbar өлшемімен дәл бірдей метрика емес. SQL саны wrapper шақырулары арқылы саналды. Медианалар бес нәтижеден бөлек есептелді.')
p('Әр кезең жаңа management-команда процесінде өлшенді; алғашқы жауаптың шаблон жүктеу шығыны алынып тасталмады. Кэште жоқ жауапты өлшерде әр сұрау алдында cache.clear() орындалды. Жауап кэште болғанда бір жылыту сұрауы жасалып, содан кейінгі бес жауап өлшенді. SQLite пен операциялық жүйенің файл кэші және компьютер жүктемесі уақытқа әсер етеді.')
p('Сондықтан 115,056 мс тарихи мәні жаңа бастапқы 438,301 мс мәнімен алмастырылмайды және SQL уақытымен жалған жұпталмайды. Жаңа серияның толық бастапқы өлшемі салыстыру үшін бөлек берілді. Суреттер Toolbar қосылған бөлек сұраулардан алынған.', small=True)
h('Қорытынды')
p('Бұл жұмыста Django блогының өнімділігі нақты өлшемдер арқылы зерттелді. Бастапқы 151 SQL сұрауы N+1 мәселесін көрсетті. Байланыстарды бірге жүктеу және пікір санын аннотациялау сұраулар санын екіге түсірді. Құрама индекс сүзгілеу жоспарын жақсартты, бірақ агрегация кезіндегі уақытша сұрыптауды толық жоймады. Кэште бар жауап дерекқорға мүлде жүгінбей берілді. Сигналдар статистиканың өзгерістерден кейін жаңаруын қамтамасыз етті. Тесттер мен сақталған өлшемдер нәтижені қайта тексеруге мүмкіндік береді.')

page()
h('Тексерулер және Git тарихы')
p('Қорытынды тексеру хаттамасы: evidence/final-checks.txt. manage.py check ескерту мен қате таппады; жеті тест өтті; makemigrations --check --dry-run жаңа өзгеріс таппады. /posts/, /stats/ және CSS нақты HTTP 200 жауабын қайтарды. Индекс жоспарда бар, деректердің SHA256 сомалары сақталған.')
table(['Тест тобы', 'Нақты тексерілген нәтиже'], [
    ['PostListTests (3 тест)', 'Кэште жоқ жауап: 2 SQL; кэштен табылуы: 0 SQL; 50 жазба; body жүктелмейді; автор, тақырыптар және пікір саны дұрыс.'],
    ['BlogStatsTests (4 тест)', 'Статистика: 2/0 SQL; қосу, сақтау, жою сигналдары; танымал 10 тақырып; M2M өзгерісі; /stats/ жауабы.'],
    ['Негізгі база', '200 автор, 50 тақырып, 20 000 жарияланым, 60 000 пікір және 60 000 байланыс өзгермеген.'],
], [160, 345])
table(['Коммит', 'Мақсаты'], [
    ['d0f58cc · step1-seed', 'Жоба, деректер және бастапқы бет'],
    ['9c6ed61 · step2-logging', 'LOGGING және TimingMiddleware'],
    ['e895512 · step3-profiling', 'Toolbar және бастапқы тест/өлшем'],
    ['05cdc38 · step4-nplus1', 'N+1 түзету және аралық өлшемдер'],
    ['1b8a707 · step5-index', 'Құрама индекс және EXPLAIN'],
    ['cef4e75 · step6-cache', 'Кэштеу, сигналдар және тексерулер'],
    ['step7-report', 'Осы есеп, скриншоттар және қорытынды хаттамалар'],
], [210, 295])
h('Іске қосу және қорғауда көрсету')
code('.\\.venv\\Scripts\\python.exe manage.py migrate\n.\\.venv\\Scripts\\python.exe manage.py check\n.\\.venv\\Scripts\\python.exe manage.py runserver 127.0.0.1:8012')
p('Мекенжайлар: http://127.0.0.1:8012/posts/ және /stats/. Базада деректер бар болса, seed командасын қайта орындамау керек. Жаңа ортада алдымен requirements.txt орнатылып, бос базаға seed бір рет орындалады.')
p('Қорғауда бастапқы 151 сұраулық SQL панелін, 151 != 2 қатесін, түзетілген QuerySet пен екі сұраулық тестті, EXPLAIN жоспарларының айырмасын және кэштегі 0 SQL жауабын көрсету қажет. Соңында статистиканың сигнал арқылы жаңаруын, барлық бес өлшемді және Git кезеңдерін түсіндіру керек.')

for chunk, caption in [(labels[:4], 'А қосымшасы. Бастапқы және аралық бес өлшем'), (labels[4:], 'Ә қосымшасы. Соңғы кезеңдердің бес өлшемі')]:
    page()
    h(caption)
    p('Әр жол - нақты жеке сұрау. Уақыт бірлігі - миллисекунд. Төмендегі медианалар SQL уақыты мен бет уақыты үшін бөлек есептелген.', small=True)
    for label in chunk:
        d = data[label]
        h(names[label])
        rows = [[r['run'], r['sql'], number(r['sql_ms']), number(r['page_ms'])] for r in d['runs']]
        rows.append(['Медиана', d['runs'][0]['sql'], number(d['median_sql_ms']), number(d['median_page_ms'])])
        table(['№', 'SQL саны', 'SQL уақыты, мс', 'Бет уақыты, мс'], rows, [80, 85, 170, 170], compact=True)

page()
h('Б қосымшасы. SQL панеліндегі нақты нәтиже')
picture('step6-sql.png', '4-сурет. Кэште жоқ жауап: негізгі агрегация және тақырыптарға бөлек сұрау, барлығы 2 SQL.', width=450)
picture('cache-hit-sql.png', '5-сурет. Сол URL қайта ашылғанда: 0 SQL. Toolbar өз шығынын қосады.', width=450)
p('Ресми анықтамалар: docs.djangoproject.com/en/5.2/topics/db/optimization/; docs.djangoproject.com/en/5.2/topics/cache/; django-debug-toolbar.readthedocs.io/en/stable/. Талаптар пайдаланушы берген 11-апта тапсырмасынан алынды; презентация файлы берілген жоқ.', small=True)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Arial', 8)
    canvas.setFillColor(colors.HexColor('#516675'))
    canvas.drawString(44, 26, 'Қали Диханбай · №11 зертханалық жұмыс · 12.11.2026')
    canvas.drawRightString(A4[0] - 44, 26, f'{doc.page}')
    canvas.restoreState()


target = OUT / 'Қали_Диханбай_ЗС11.pdf'
SimpleDocTemplate(str(target), pagesize=A4, rightMargin=44, leftMargin=44,
                  topMargin=40, bottomMargin=44, title='Django өнімділігі - №11 зертханалық жұмыс',
                  author='Қали Диханбай').build(story, onFirstPage=footer, onLaterPages=footer)
(OUT / 'Қали_Диханбай_ЗС11.md').write_text('\n'.join(markdown), encoding='utf-8')
print(target)
