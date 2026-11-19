import sqlite3

from debug_toolbar.middleware import show_toolbar
from django.db import DatabaseError
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from openai import OpenAIError

from .forms import AskForm
from .guard import NO_ANSWER_SQL, UnsafeSQLError, run_readonly
from .llm import ask_sql
from .models import QueryLog


def show_toolbar_outside_report(request):
    return show_toolbar(request) and request.path != reverse('shop:report')


@require_http_methods(['GET', 'POST'])
def report(request):
    form = AskForm(request.POST if request.method == 'POST' else None)
    context = {'form': form}
    if request.method == 'POST' and form.is_valid():
        question = form.cleaned_data['question']
        sql = error = ''
        try:
            sql = ask_sql(question, mode='improved')
            if sql == NO_ANSWER_SQL:
                context['no_answer'] = True
            else:
                context['columns'], context['rows'] = run_readonly(sql)
        except UnsafeSQLError:
            sql = ''
            error = 'Жасалған SQL сұрауы қауіпсіздік тексеруінен өтпеді.'
        except (OpenAIError, IndexError):
            error = 'Жасанды интеллект қызметінен жауап алу мүмкін болмады. Кейінірек қайталап көріңіз.'
        except (sqlite3.Error, OSError):
            error = 'Есепті орындау мүмкін болмады. Сұрағыңызды өзгертіп, қайталап көріңіз.'

        try:
            QueryLog.objects.create(question=question, sql=sql, error=error)
        except DatabaseError:
            context['log_error'] = 'Сұрауды журналға сақтау мүмкін болмады.'
        context.update(sql=sql, error=error)
    return render(request, 'shop/report.html', context)
