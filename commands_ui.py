"""
core/commands_ui.py — обработка slash-команд (/help, /config, /model и т.д.)
Отделено от бизнес-логики, чтобы не превращать main в помойку.
"""

import json
from pathlib import Path

from config import PROVIDER_DEFAULTS, CONFIG_FILE
from core.config_manager import load_config, update_config_key, save_config
from core.context import check_tools


HELP_TEXT = """
┌─────────────────────────────────────────────┐
│           Terminal AI — команды             │
├──────────────┬──────────────────────────────┤
│ /help        │ это меню                     │
│ /clear       │ очистить историю диалога     │
│ /history     │ показать историю сессии      │
│ /context     │ показать контекст среды      │
│ /config      │ показать конфиг              │
│ /provider    │ сменить провайдера           │
│ /model       │ сменить модель               │
│ /auto        │ вкл/выкл авто-подтверждение  │
│ /tools       │ проверить доступные утилиты  │
│ /exit /quit  │ выйти                        │
└──────────────┴──────────────────────────────┘

Режим: агент. Каждый запрос — многошаговое выполнение.
Модель сама читает файлы, выполняет команды, пишет код.
"""


def handle_slash_command(cmd: str, llm_client, cfg: dict) -> tuple[bool, bool]:
    """
    Обработать slash-команду.
    Возвращает (handled: bool, should_exit: bool).
    """
    cmd = cmd.strip().lower()
    parts = cmd.split(None, 1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    if command in ("/exit", "/quit", "/q"):
        print("Пока.")
        return True, True

    elif command == "/help":
        print(HELP_TEXT)
        return True, False

    elif command == "/clear":
        llm_client.clear_history()
        return True, False

    elif command == "/history":
        if not llm_client.history:
            print("[i] История пуста.")
        else:
            print(f"\nИстория сессии ({len(llm_client.history)} сообщений):\n")
            for i, msg in enumerate(llm_client.history, 1):
                role = "you" if msg["role"] == "user" else "ai"
                content = msg["content"]
                # Обрезаем длинные сообщения для отображения
                if len(content) > 200:
                    content = content[:200] + "..."
                print(f"  [{i}] {role}> {content}")
        return True, False

    elif command == "/context":
        from core.context import collect_context
        ctx = collect_context(enabled=True)
        print("\nТекущий контекст:\n")
        print(ctx)
        return True, False

    elif command == "/config":
        current_cfg = load_config()
        # Скрываем ключ, показываем только первые 8 символов
        display = dict(current_cfg)
        key = display.get("api_key", "")
        if len(key) > 8:
            display["api_key"] = key[:8] + "..." + key[-4:]
        print(f"\nКонфиг ({CONFIG_FILE}):\n")
        print(json.dumps(display, indent=2, ensure_ascii=False))
        return True, False

    elif command == "/provider":
        if args:
            providers = list(PROVIDER_DEFAULTS.keys())
            if args in providers:
                defaults = PROVIDER_DEFAULTS[args]
                cfg_data = load_config()
                cfg_data["provider"] = args
                cfg_data["base_url"] = defaults["base_url"]
                cfg_data["model"] = defaults["model"]
                save_config(cfg_data)
                # Обновить клиент
                from openai import OpenAI
                llm_client.client = OpenAI(
                    api_key=cfg_data["api_key"],
                    base_url=cfg_data["base_url"]
                )
                llm_client.model = cfg_data["model"]
                print(f"[✓] Провайдер: {args}, модель: {cfg_data['model']}")
            else:
                print(f"[!] Неизвестный провайдер. Доступные: {', '.join(providers)}")
        else:
            providers = list(PROVIDER_DEFAULTS.keys())
            print("Доступные провайдеры:")
            for i, p in enumerate(providers, 1):
                m = PROVIDER_DEFAULTS[p]["model"]
                print(f"  {i}. {p}  (модель по умолч.: {m})")
            print(f"\nИспользование: /provider groq")
        return True, False

    elif command == "/model":
        if args:
            llm_client.model = args
            update_config_key("model", args)
        else:
            current = load_config().get("model", "?")
            print(f"Текущая модель: {current}")
            print("Использование: /model llama-3.3-70b-versatile")
        return True, False

    elif command == "/auto":
        cfg_data = load_config()
        current = cfg_data.get("auto_confirm", False)
        new_val = not current
        update_config_key("auto_confirm", new_val)
        cfg["auto_confirm"] = new_val
        status = "ВКЛЮЧЁН" if new_val else "ВЫКЛЮЧЕН"
        if new_val:
            print(f"[!] Авто-подтверждение {status}. Команды будут выполняться без вопросов.")
            print("    Опасные команды всё равно потребуют подтверждения.")
        else:
            print(f"[✓] Авто-подтверждение {status}. Каждое действие требует одобрения.")
        return True, False

    elif command == "/tools":
        print("\nДоступные инструменты:")
        tools = check_tools()
        for tool, available in tools.items():
            mark = "✓" if available else "✗"
            print(f"  [{mark}] {tool}")
        return True, False

    return False, False
