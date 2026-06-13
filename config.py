"""
config.py — константы, пути, дефолты.
Всё в одном месте, чтобы не охотиться за магическими строками по всему проекту.
"""

import os
from pathlib import Path

# --- Пути ---
DATA_DIR = Path(__file__).parent / "data"
CONFIG_FILE = DATA_DIR / "config.json"
HISTORY_FILE = DATA_DIR / "history.jsonl"

# --- Провайдеры ---
PROVIDER_DEFAULTS = {
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "key_prefix": "gsk_",
    },
    "openai": {
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "key_prefix": "sk-",
    },
    "openrouter": {
        "model": "meta-llama/llama-3.3-70b-instruct",
        "base_url": "https://openrouter.ai/api/v1",
        "key_prefix": "sk-or-",
    },
    "gemini": {
        "model": "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_prefix": "AIza",
    },
}

KEY_PREFIX_MAP = {
    v["key_prefix"]: k for k, v in PROVIDER_DEFAULTS.items()
}

# --- LLM параметры ---
LLM_TEMPERATURE = 0.2      # пониже — меньше фантазий при генерации команд
LLM_MAX_TOKENS = 2048

# --- Безопасность ---
# Команды, которые требуют ЯВНОГО подтверждения даже в auto-режиме
DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -r",
    "sudo rm",
    "mkfs",
    "dd if=",
    "> /dev/",
    "chmod 777",
    ":(){ :|:& };:",   # fork bomb — на всякий случай
]

# --- Системный промпт ---
SYSTEM_PROMPT = """\
Ты — терминальный ИИ-ассистент. Работаешь в командной строке (Linux/Android Termux).

Правила ответа:
1. Если нужно выполнить команду — возвращай ТОЛЬКО валидный JSON, без markdown-обёрток.
2. Если это обычный вопрос — отвечай текстом.
3. Будь лаконичен. Терминал — не место для лекций.

Форматы JSON-ответов:

Команда shell:
{"type": "command", "command": "git status", "description": "Проверить статус репозитория"}

Создать/перезаписать файл:
{"type": "write_file", "path": "README.md", "content": "# Проект\\n...", "description": "Создать README"}

Прочитать файл:
{"type": "read_file", "path": "main.py", "description": "Прочитать main.py"}

Патч файла (unified diff):
{"type": "patch", "path": "main.py", "diff": "--- a/main.py\\n+++ b/main.py\\n...", "description": "Исправить баг"}

Несколько действий подряд:
{"type": "sequence", "steps": [...], "description": "Общее описание"}

Текстовый ответ (не требует JSON):
Просто пиши обычный текст.
"""