"""
core/config_manager.py — читаем, пишем, создаём конфиг.
Мастер настройки при первом запуске.
"""

import json
import sys
from pathlib import Path

from config import (
    CONFIG_FILE,
    DATA_DIR,
    KEY_PREFIX_MAP,
    PROVIDER_DEFAULTS,
)


def config_exists() -> bool:
    return CONFIG_FILE.exists()


def load_config() -> dict:
    """Загрузить конфиг. Упадёт с понятной ошибкой, если файл битый."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[!] Конфиг повреждён: {e}")
        print(f"[!] Удали {CONFIG_FILE} и запусти снова.")
        sys.exit(1)


def save_config(cfg: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def detect_provider(api_key: str) -> str | None:
    """
    Определить провайдера по префиксу ключа.
    Длинные префиксы проверяются первыми (sk-or- раньше sk-).
    """
    for prefix in sorted(KEY_PREFIX_MAP.keys(), key=len, reverse=True):
        if api_key.startswith(prefix):
            return KEY_PREFIX_MAP[prefix]
    return None


def setup_wizard() -> dict:
    """
    Интерактивный мастер первого запуска.
    Минимум вопросов — максимум работы.
    """
    print("\n" + "═" * 50)
    print("  Terminal AI — первый запуск")
    print("═" * 50)
    print("\nПоддерживаемые провайдеры:")
    print("  gsk_...      → Groq (быстро и бесплатно)")
    print("  sk-...       → OpenAI")
    print("  sk-or-...    → OpenRouter")
    print("  AIza...      → Google Gemini")
    print()

    # --- API ключ ---
    while True:
        api_key = input("Введите API ключ: ").strip()
        if not api_key:
            print("[!] Ключ не может быть пустым.")
            continue

        provider = detect_provider(api_key)
        if provider:
            print(f"[✓] Провайдер определён автоматически: {provider}")
            break
        else:
            # Ключ нераспознан — спросим провайдера вручную
            print("[?] Провайдер не определён по префиксу ключа.")
            providers = list(PROVIDER_DEFAULTS.keys())
            for i, p in enumerate(providers, 1):
                print(f"  {i}. {p}")
            choice = input("Выберите номер провайдера: ").strip()
            try:
                idx = int(choice) - 1
                provider = providers[idx]
                break
            except (ValueError, IndexError):
                print("[!] Неверный выбор, попробуй ещё раз.")

    defaults = PROVIDER_DEFAULTS[provider]
    default_model = defaults["model"]

    # --- Модель ---
    print(f"\nМодель по умолчанию: {default_model}")
    model_input = input("Нажми Enter чтобы принять, или введи другую: ").strip()
    model = model_input if model_input else default_model

    cfg = {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": defaults["base_url"],
        "auto_confirm": False,   # по умолчанию всегда спрашиваем
        "context_enabled": True, # собирать контекст системы
    }

    save_config(cfg)

    print(f"\n[✓] Конфиг сохранён: {CONFIG_FILE}")
    print("═" * 50 + "\n")
    return cfg


def update_config_key(key: str, value) -> None:
    """Обновить одно поле конфига без перезаписи всего."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    print(f"[✓] {key} = {value}")