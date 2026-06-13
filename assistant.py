#!/usr/bin/env python3
"""
assistant.py — точка входа. REPL с агентом по умолчанию.
Запуск: python assistant.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR
from core.config_manager import config_exists, load_config, setup_wizard
from core.installer import install_dependencies, check_termux_deps
from core.llm import LLMClient
from core.agent import run_agent
from core.commands_ui import handle_slash_command
from core.context import collect_context


BANNER = """
╔══════════════════════════════════════╗
║         Terminal AI Assistant        ║
║   /help — команды  |  Ctrl+C — выход ║
╚══════════════════════════════════════╝"""


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not config_exists():
        install_dependencies()
        check_termux_deps()
        cfg = setup_wizard()
    else:
        cfg = load_config()

    print(BANNER)

    try:
        from openai import OpenAI  # noqa: F401
    except ImportError:
        print("[!] Пакет openai не найден. Устанавливаю...")
        install_dependencies()

    try:
        llm = LLMClient(cfg)
    except Exception as e:
        print(f"[!] Ошибка инициализации LLM: {e}")
        sys.exit(1)

    auto_confirm = cfg.get("auto_confirm", False)
    context_enabled = cfg.get("context_enabled", True)

    if auto_confirm:
        print("[!] Авто-подтверждение включено.")

    print(f"[✓] Провайдер: {cfg['provider']} | Модель: {cfg['model']}")
    print(f"[✓] Режим: агент (каждый запрос — многошаговое выполнение)")
    print()

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
                auto_confirm = cfg.get("auto_confirm", False)
                continue
            # Нераспознанная slash-команда — уходит в агент как обычный текст

        # Контекст среды
        system_ctx = collect_context(enabled=context_enabled)

        # Всё идёт через агентный цикл
        run_agent(
            task=user_input,
            llm=llm,
            system_context=system_ctx,
            auto_confirm=auto_confirm,
        )

        print()


if __name__ == "__main__":
    main()
