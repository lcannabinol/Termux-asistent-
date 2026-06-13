"""
core/agent.py — агентный цикл.

Модель работает итерационно: получает результат каждого действия,
решает что делать дальше, пока сама не скажет {"type": "done"}.
Человек подтверждает каждый шаг (или нет, если auto_confirm).
"""

from __future__ import annotations

import json
import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.llm import LLMClient

from core.commands import dispatch_action
from config import HISTORY_FILE

MAX_STEPS = 20   # защита от бесконечного цикла — на всякий случай

# Промпт, который объясняет модели что она в агент-режиме
AGENT_SYSTEM_ADDENDUM = """
Ты работаешь в режиме агента. Ты можешь выполнять несколько действий подряд.

После каждого действия ты получишь его результат и продолжишь работу.
Когда задача полностью выполнена — верни:
{"type": "done", "summary": "Что было сделано"}

Если что-то пошло не так и продолжать нет смысла — верни:
{"type": "error", "message": "Что случилось и почему остановился"}

Планируй заранее. Не делай лишних шагов.
Перед изменением файла — сначала прочитай его (read_file), если не уверен в содержимом.
"""


def run_agent(
    task: str,
    llm: "LLMClient",
    system_context: str = "",
    auto_confirm: bool = False,
) -> None:
    """
    Запустить агентный цикл для задачи task.

    Модель получает задачу → возвращает действие → мы выполняем →
    возвращаем результат модели → она решает что дальше → repeat.
    """
    print(f"\n[agent] Задача: {task}")
    print(f"[agent] Максимум шагов: {MAX_STEPS}")
    print("─" * 50)

    # Формируем расширенный системный промпт для агент-режима
    from config import SYSTEM_PROMPT
    agent_system = SYSTEM_PROMPT + "\n\n" + AGENT_SYSTEM_ADDENDUM
    if system_context:
        agent_system += f"\n\nТекущий контекст рабочей среды:\n{system_context}"

    # Первый запрос — сама задача
    messages: list[dict] = [
        {"role": "system", "content": agent_system},
        {"role": "user", "content": task},
    ]

    step = 0

    while step < MAX_STEPS:
        step += 1
        print(f"\n[agent → шаг {step}]")

        # Запрос к модели
        reply = _call_llm(llm, messages)
        if not reply:
            print("[agent] Пустой ответ от модели. Стоп.")
            break

        # Добавляем ответ в историю
        messages.append({"role": "assistant", "content": reply})

        # Пробуем распарсить действие
        action = llm.try_parse_action(reply)

        if not action:
            # Обычный текст — модель что-то объясняет или отвечает
            print(reply)
            # Если это финальный текст без JSON — считаем задачу выполненной
            break

        action_type = action.get("type")

        # --- Завершение ---
        if action_type == "done":
            summary = action.get("summary", "")
            print(f"\n[agent ✓] Готово.")
            if summary:
                print(f"[agent] {summary}")
            break

        if action_type == "error":
            msg = action.get("message", "")
            print(f"\n[agent ✗] Агент остановился: {msg}")
            break

        # --- Выполнить действие ---
        result = dispatch_action(action, auto_confirm=auto_confirm)

        # Формируем фидбек для модели
        feedback = _build_feedback(action, result)

        # Добавляем результат в историю как user-сообщение
        messages.append({"role": "user", "content": feedback})

    else:
        print(f"\n[agent] Достигнут лимит шагов ({MAX_STEPS}). Остановлено.")

    print("─" * 50)

    # Сохранить сессию в history.jsonl
    _save_history(task, messages)


def _save_history(task: str, messages: list[dict]) -> None:
    """Дописать сессию в history.jsonl."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "task": task,
            "steps": len(messages),
            "messages": messages,
        }
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass  # история — не критична, не падаем


def _call_llm(llm: "LLMClient", messages: list[dict]) -> str:
    """
    Прямой вызов LLM с полной историей сообщений.
    В отличие от llm.ask() — не трогаем llm.history, управляем сами.
    """
    try:
        response = llm.client.chat.completions.create(
            model=llm.model,
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"[agent] Ошибка LLM: {e}")
        return ""


def _build_feedback(action: dict, result: str) -> str:
    """
    Сформировать сообщение с результатом действия для передачи модели.
    Кратко и по делу — не засоряем контекст.
    """
    action_type = action.get("type", "?")
    desc = action.get("description", "")

    if result == "ok":
        return f"[Результат шага] {action_type} выполнен успешно. {desc}"

    elif result == "error":
        return f"[Результат шага] {action_type} завершился с ошибкой. Реши как продолжить."

    else:
        # read_file возвращает содержимое
        path = action.get("path", "файл")
        # Обрезаем если очень длинный файл — не стоит гнать 10к токенов
        content = result
        if len(content) > 6000:
            content = content[:6000] + f"\n\n[... обрезано, файл больше 6000 символов ...]"
        return f"[Результат шага] Содержимое '{path}':\n\n{content}"