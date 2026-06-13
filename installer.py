"""
core/installer.py — проверка и установка зависимостей.
Потому что пользователь не обязан помнить про pip install каждый раз.
"""

import subprocess
import sys


REQUIRED_PACKAGES = ["openai"]   # всё через openai-совместимый интерфейс


def check_package(package: str) -> bool:
    """Проверить, установлен ли Python-пакет."""
    try:
        __import__(package.replace("-", "_"))
        return True
    except ImportError:
        return False


def install_package(package: str) -> bool:
    """Установить пакет через pip."""
    print(f"[→] Установка {package}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", package, "--quiet"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[✓] {package} установлен.")
        return True
    else:
        print(f"[!] Ошибка установки {package}:")
        print(result.stderr[:500])
        return False


def install_dependencies() -> bool:
    """
    Проверить и установить все зависимости.
    Возвращает True если всё ок.
    """
    all_ok = True

    for pkg in REQUIRED_PACKAGES:
        if not check_package(pkg):
            ok = install_package(pkg)
            if not ok:
                all_ok = False

    if all_ok:
        print("[✓] Все зависимости установлены.")
    else:
        print("[!] Часть зависимостей не установлена. Некоторые функции могут не работать.")

    return all_ok


def check_termux_deps() -> None:
    """
    Для Termux: проверить наличие системных пакетов.
    Не устанавливать автоматически — только предупредить.
    """
    from core.context import missing_termux_packages, check_tools
    from pathlib import Path

    if not Path("/data/data/com.termux").exists():
        return

    missing = missing_termux_packages()
    if missing:
        print("\n[i] В Termux отсутствуют некоторые пакеты:")
        for pkg in missing:
            print(f"    pkg install {pkg}")
        print()
