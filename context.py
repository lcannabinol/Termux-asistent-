"""
core/context.py — собираем контекст рабочей среды перед каждым запросом.
Модель должна знать где она и что вокруг. Как нормальный разработчик.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path


def _run(cmd: str) -> str:
    """Выполнить команду, вернуть stdout или пустую строку при ошибке."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=3, encoding="utf-8", errors="replace"
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _available(tool: str) -> bool:
    return shutil.which(tool) is not None


def collect_context(enabled: bool = True) -> str:
    """
    Собрать контекст текущей среды.
    Возвращает строку для вставки в системный промпт.
    """
    if not enabled:
        return ""

    ctx: dict = {}

    # --- Рабочая директория ---
    ctx["cwd"] = os.getcwd()

    # --- Git ---
    if _available("git"):
        branch = _run("git branch --show-current 2>/dev/null")
        if branch:
            ctx["git_branch"] = branch
            status = _run("git status --short 2>/dev/null")
            if status:
                # Берём не больше 20 строк, чтобы не засорять контекст
                lines = status.split("\n")[:20]
                ctx["git_status"] = lines
                if len(status.split("\n")) > 20:
                    ctx["git_status_truncated"] = True

    # --- Файлы в текущей директории ---
    try:
        entries = sorted(Path(".").iterdir(), key=lambda p: (p.is_file(), p.name))
        files = []
        dirs = []
        for e in entries[:30]:  # не больше 30 записей
            if e.name.startswith("."):
                continue
            if e.is_dir():
                dirs.append(e.name + "/")
            else:
                files.append(e.name)
        ctx["dirs"] = dirs
        ctx["files"] = files
    except PermissionError:
        pass

    # --- Python окружение ---
    if _available("python3") or _available("python"):
        py = _run("python3 --version 2>/dev/null") or _run("python --version 2>/dev/null")
        if py:
            ctx["python"] = py

        # Есть ли виртуальное окружение?
        if os.environ.get("VIRTUAL_ENV"):
            ctx["venv"] = Path(os.environ["VIRTUAL_ENV"]).name

    # --- Node/npm ---
    if _available("node"):
        node_v = _run("node --version 2>/dev/null")
        if node_v:
            ctx["node"] = node_v

    # --- Termux detection ---
    if Path("/data/data/com.termux").exists() or "com.termux" in os.environ.get("PREFIX", ""):
        ctx["platform"] = "termux/android"
    else:
        ctx["platform"] = "linux"

    return json.dumps(ctx, ensure_ascii=False, indent=2)


def check_tools() -> dict[str, bool]:
    """Проверить наличие основных инструментов."""
    tools = ["git", "python3", "pip3", "node", "npm", "curl", "wget", "rg", "fzf"]
    return {tool: _available(tool) for tool in tools}


def missing_termux_packages() -> list[str]:
    """
    Вернуть список пакетов Termux, которые отсутствуют.
    Вызывается только в Termux.
    """
    pkg_map = {
        "git": "git",
        "python3": "python",
        "rg": "ripgrep",
        "node": "nodejs",
    }
    missing = []
    for tool, pkg in pkg_map.items():
        if not _available(tool):
            missing.append(pkg)
    return missing