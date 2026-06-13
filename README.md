# Terminal AI Assistant

Терминальный ИИ-ассистент. Работает через Groq, OpenAI, OpenRouter, Gemini.
Запускается в Linux и Android Termux.

## Быстрый старт

```bash
pip install openai
python assistant.py
```

При первом запуске — мастер настройки. Вводишь API ключ, остальное определяется автоматически.

## Поддерживаемые провайдеры

| Префикс ключа | Провайдер  | Модель по умолчанию           |
|---------------|------------|-------------------------------|
| `gsk_`        | Groq       | llama-3.3-70b-versatile       |
| `sk-`         | OpenAI     | gpt-4o-mini                   |
| `sk-or-`      | OpenRouter | meta-llama/llama-3.3-70b-...  |
| `AIza`        | Gemini     | gemini-2.0-flash              |

## Команды

```
/help       — список команд
/clear      — очистить историю диалога
/context    — показать текущий контекст среды
/config     — показать конфиг
/provider   — сменить провайдера
/model      — сменить модель
/auto       — вкл/выкл авто-подтверждение команд
/tools      — проверить доступные утилиты
/exit       — выйти
```

## Структура проекта

```
terminal-ai/
├── assistant.py          # точка входа, REPL
├── config.py             # константы, дефолты, системный промпт
├── requirements.txt
├── core/
│   ├── llm.py            # единый интерфейс к LLM
│   ├── commands.py       # выполнение действий (shell, write_file, patch...)
│   ├── commands_ui.py    # slash-команды
│   ├── config_manager.py # чтение/запись конфига, мастер установки
│   ├── context.py        # сбор контекста среды (pwd, git, файлы)
│   └── installer.py      # проверка зависимостей
└── data/
    ├── config.json        # конфиг (создаётся автоматически)
    └── history.jsonl      # история (зарезервировано для Этапа 5)
```

## Протокол действий (JSON от модели)

```json
{"type": "command",    "command": "git status"}
{"type": "write_file", "path": "README.md", "content": "..."}
{"type": "read_file",  "path": "main.py"}
{"type": "patch",      "path": "app.py", "diff": "..."}
{"type": "sequence",   "steps": [...]}
```

## Этапы разработки

- [x] Этап 1 — минимально рабочий ассистент
- [ ] Этап 2 — провайдеры (уже абстрагированы через openai-совместимый API)
- [ ] Этап 3 — безопасное выполнение команд (реализовано)
- [ ] Этап 4 — контекст системы (реализован)
- [ ] Этап 5 — режим агента (многошаговый)
- [ ] Этап 6 — Android/Termux особенности (базовые проверки есть)
