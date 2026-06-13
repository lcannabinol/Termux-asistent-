"""
core/commands.py — безопасное выполнение действий от модели.
LLM предлагает — человек решает. Революционная концепция.
"""

import os
import subprocess
import sys
from pathlib import Path

from config import DANGEROUS_PATTERNS


# ─── Проверка безопасности ────────────────────────────────────────────────────

def is_dangerous(command: str) -> bool:
    """Проверить, содержит ли команда опасные паттерны."""
    cmd_lower = command.lower()
    return any(pattern in cmd_lower for pattern in DANGEROUS_PATTERNS)


def confirm(prompt: str, default_yes: bool = False, force_confirm: bool = False) -> bool:
    """
    Запросить подтверждение у пользователя.
    force_confirm=True — спрашивать даже в auto-режиме (для опасных команд).
    """
    suffix = "[Y/n]" if default_yes else "[y/N]"
    try:
        answer = input(f"{prompt} {suffix}: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n[!] Отменено.")
        return False

    if answer == "":
        return default_yes
    return answer in ("y", "yes", "да", "д")


# ─── Вывод действий ───────────────────────────────────────────────────────────

def print_action(action: dict) -> None:
    """Красиво показать что собирается сделать модель."""
    t = action.get("type", "?")
    desc = action.get("description", "")

    print("\n" + "─" * 50)
    if desc:
        print(f"  📋 {desc}")
    print(f"  Тип: {t}")

    if t == "command":
        print(f"  $ {action.get('command', '')}")
    elif t == "write_file":
        path = action.get("path", "")
        content = action.get("content", "")
        lines = content.count("\n") + 1
        print(f"  Файл: {path}  ({lines} строк)")
    elif t == "read_file":
        print(f"  Файл: {action.get('path', '')}")
    elif t == "patch":
        print(f"  Файл: {action.get('path', '')}")
        diff_preview = action.get("diff", "")[:300]
        if diff_preview:
            print(f"  Diff preview:\n{diff_preview}")
    elif t == "sequence":
        steps = action.get("steps", [])
        print(f"  Шагов: {len(steps)}")
        for i, step in enumerate(steps, 1):
            step_type = step.get("type", "?")
            step_desc = step.get("description") or step.get("command") or step.get("path", "")
            print(f"    {i}. [{step_type}] {step_desc}")

    print("─" * 50)


# ─── Исполнители ──────────────────────────────────────────────────────────────

def run_command(command: str) -> tuple[int, str, str]:
    """Выполнить shell-команду. Вернуть (returncode, stdout, stderr)."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode, result.stdout, result.stderr


def execute_command_action(action: dict, auto_confirm: bool = False) -> bool:
    """Выполнить action типа 'command'."""
    command = action.get("command", "").strip()
    if not command:
        print("[!] Пустая команда.")
        return False

    dangerous = is_dangerous(command)
    if dangerous:
        print("\n⚠️  ВНИМАНИЕ: команда содержит потенциально опасные операции!")

    if not auto_confirm or dangerous:
        if not confirm("Выполнить команду?", default_yes=not dangerous):
            print("[—] Пропущено.")
            return False

    code, out, err = run_command(command)

    if out:
        print(out, end="")
    if err:
        print(err, end="", file=sys.stderr)
    if code != 0:
        print(f"\n[!] Команда завершилась с кодом {code}")
        return False

    return True


def execute_write_file_action(action: dict, auto_confirm: bool = False) -> bool:
    """Создать или перезаписать файл."""
    path = action.get("path", "").strip()
    content = action.get("content", "")

    if not path:
        print("[!] Не указан путь к файлу.")
        return False

    file_path = Path(path)
    exists = file_path.exists()
    verb = "Перезаписать" if exists else "Создать"

    if not auto_confirm:
        if not confirm(f"{verb} файл '{path}'?", default_yes=True):
            print("[—] Пропущено.")
            return False

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    lines = content.count("\n") + 1
    print(f"[✓] {verb.lower()} '{path}' ({lines} строк)")
    return True


def execute_read_file_action(action: dict) -> str:
    """Прочитать файл и вернуть содержимое (для передачи модели)."""
    path = action.get("path", "").strip()
    if not path:
        return "[!] Не указан путь."

    file_path = Path(path)
    if not file_path.exists():
        return f"[!] Файл не найден: {path}"

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        print(f"[✓] Прочитан '{path}' ({len(content)} символов)")
        return content
    except PermissionError:
        return f"[!] Нет доступа к '{path}'"


def execute_patch_action(action: dict, auto_confirm: bool = False) -> bool:
    """Применить unified diff к файлу через patch."""
    path = action.get("path", "").strip()
    diff = action.get("diff", "").strip()

    if not path or not diff:
        print("[!] Не указан путь или diff.")
        return False

    if not auto_confirm:
        if not confirm(f"Применить патч к '{path}'?", default_yes=True):
            print("[—] Пропущено.")
            return False

    # Записываем diff во временный файл
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch",
                                     delete=False, encoding="utf-8") as tmp:
        tmp.write(diff)
        tmp_path = tmp.name

    code, out, err = run_command(f"patch '{path}' '{tmp_path}'")
    os.unlink(tmp_path)

    if out:
        print(out, end="")
    if err:
        print(err, end="")
    if code != 0:
        print(f"[!] patch завершился с кодом {code}")
        return False

    print(f"[✓] Патч применён к '{path}'")
    return True


# ─── Диспетчер ────────────────────────────────────────────────────────────────

def dispatch_action(action: dict, auto_confirm: bool = False) -> str:
    """
    Выполнить любое действие от модели.
    Возвращает строку с результатом (для передачи обратно в модель в агент-режиме).
    """
    print_action(action)
    t = action.get("type")

    if t == "command":
        success = execute_command_action(action, auto_confirm)
        return "ok" if success else "error"

    elif t == "write_file":
        success = execute_write_file_action(action, auto_confirm)
        return "ok" if success else "error"

    elif t == "read_file":
        content = execute_read_file_action(action)
        return content

    elif t == "patch":
        success = execute_patch_action(action, auto_confirm)
        return "ok" if success else "error"

    elif t == "sequence":
        results = []
        for i, step in enumerate(action.get("steps", []), 1):
            print(f"\n[→] Шаг {i}/{len(action['steps'])}")
            result = dispatch_action(step, auto_confirm)
            results.append(result)
            if result == "error":
                print(f"[!] Последовательность прервана на шаге {i}.")
                break
        return "\n".join(results)

    else:
        print(f"[!] Неизвестный тип действия: {t}")
        return "error"