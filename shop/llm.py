import os
from pathlib import Path

from django.conf import settings
from dotenv import load_dotenv
from openai import OpenAI

from .guard import extract_sql, validate_sql
from .prompts import build_system_prompt


def ask_llm(system, user):
    load_dotenv(Path(settings.BASE_DIR) / '.env', override=False)
    with OpenAI(
        base_url=os.getenv('LLM_BASE_URL', 'http://localhost:11434/v1'),
        api_key=os.getenv('LLM_API_KEY', 'ollama'),
        timeout=60.0,
        max_retries=0,
    ) as client:
        response = client.chat.completions.create(
            model=os.getenv('LLM_MODEL', 'qwen2.5-coder:1.5b'),
            temperature=0,
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user},
            ],
        )
    return response.choices[0].message.content


def ask_sql(question, mode='improved'):
    system = build_system_prompt(mode)
    return validate_sql(extract_sql(ask_llm(system, question)))
