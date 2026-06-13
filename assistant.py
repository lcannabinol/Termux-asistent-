#!/usr/bin/env python3
"""
assistant.py — точка входа. REPL-цикл.
Запуск: python assistant.py
"""

import sys
import os

# Добавляем корень проекта в path, чтобы импорты работали
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR
from core.config_manager import config_exists, load_config, setup_wizard
from core.installer import install_dependencies, check_termux_deps
from core.llm import LLMClient
from core.commands import dispatch_action
from core.commands_ui import handle_slash_command
from core.context import collect_context


BANNER = """
╔══════════════════════════════════════╗
║         Terminal AI Assistant        ║
║   /help — команды  |  Ctrl+C — выход ║
╚══════════════════════════════════════╝"""


def main():
    # --- Инициализация ---
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Первый запуск
    if not config_exists():
        install_dependencies()
        check_termux_deps()
        cfg = setup_wizard()
    else:
        cfg = load_config()

    print(BANNER)

    # Проверим зависимости при каждом старте (быстро — только check, не install)
    try:
        from openai import OpenAI  # noqa: F401
    except ImportError:
        print("[!] Пакет openai не найден. Устанавливаю...")
        install_dependencies()

    # --- LLM клиент ---
    try:
        llm = LLMClient(cfg)
    except Exception as e:
        print(f"[!] Ошибка инициализации LLM: {e}")
        sys.exit(1)

    auto_confirm = cfg.get("auto_confirm", False)
    context_enabled = cfg.get("context_enabled", True)

    if auto_confirm:
        print("[!] Авто-подтверждение включено — команды выполняются без вопросов.")

    print(f"[✓] Провайдер: {cfg['provider']} | Модель: {cfg['model']}")
    print()

    # --- REPL ---
    while True:
        try:
            user_input = input("you> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nПока.")
            break

        if not user_input:
            continue

        # Slash-команды
        if user_input.startswith("/"):
            handled, should_exit = handle_slash_command(user_input, llm, cfg)
            if should_exit:
                break
            if handled:
                # Обновить auto_confirm из cfg на случай если /auto переключили
                auto_confirm = cfg.get("auto_confirm", False)
                continue
            # Не распознанная slash-команда — отправить в LLM как обычный запрос
            # (вдруг пользователь спрашивает про /proc или /etc)

        # Контекст системы
        system_ctx = collect_context(enabled=context_enabled)

        # Запрос к модели
        print("ai> ", end="", flush=True)
        reply = llm.ask(user_input, system_context=system_ctx)

        if not reply:
            continue

        # Попытка распарсить действие
        action = llm.try_parse_action(reply)

        if action:
            # Модель хочет что-то сделать
            result = dispatch_action(action, auto_confirm=auto_confirm)

            # Если это был read_file — скормим результат обратно модели
            if action.get("type") == "read_file" and result not in ("ok", "error"):
                followup_prompt = f"Содержимое файла '{action.get('path')}':\n\n{result}\n\nПродолжи выполнение задачи."
                print("\nai> ", end="", flush=True)
                followup_reply = llm.ask(followup_prompt)
                if followup_reply:
                    followup_action = llm.try_parse_action(followup_reply)
                    if followup_action:
                        dispatch_action(followup_action, auto_confirm=auto_confirm)
                    else:
                        print(followup_reply)
        else:
            # Обычный текстовый ответ
            print(reply)

        print()


if __name__ == "__main__":
    main()