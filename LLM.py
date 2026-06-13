"""
core/llm.py — единый интерфейс ко всем провайдерам.
Снаружи один метод: ask(). Что под капотом — не твоя забота.
"""

import json
import sys
from typing import Generator

try:
    from openai import OpenAI, APIConnectionError, AuthenticationError, RateLimitError
except ImportError:
    print("[!] Пакет 'openai' не установлен. Запусти: pip install openai")
    sys.exit(1)

from config import LLM_TEMPERATURE, LLM_MAX_TOKENS, SYSTEM_PROMPT


class LLMClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg.get("base_url"),
        )
        self.model = cfg["model"]
        self.history: list[dict] = []   # история текущей сессии

    def ask(self, user_message: str, system_context: str = "") -> str:
        """
        Отправить сообщение модели, получить строку-ответ.
        system_context — дополнительный контекст (pwd, git, файлы).
        """
        system = SYSTEM_PROMPT
        if system_context:
            system += f"\n\nТекущий контекст рабочей среды:\n{system_context}"

        self.history.append({"role": "user", "content": user_message})

        messages = [{"role": "system", "content": system}] + self.history

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
        except AuthenticationError:
            print("\n[!] Ошибка авторизации. Проверь API ключ (/config).")
            self.history.pop()
            return ""
        except RateLimitError:
            print("\n[!] Превышен лимит запросов. Подожди немного.")
            self.history.pop()
            return ""
        except APIConnectionError as e:
            print(f"\n[!] Нет соединения с API: {e}")
            self.history.pop()
            return ""

        reply = response.choices[0].message.content or ""
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def clear_history(self) -> None:
        self.history.clear()
        print("[✓] История диалога очищена.")

    def try_parse_action(self, text: str) -> dict | None:
        """
        Попытаться распарсить JSON-действие из ответа модели.
        Модели иногда оборачивают JSON в ```json ... ``` — обработаем и это.
        """
        text = text.strip()

        # Убрать markdown-обёртку, если модель забыла про правила
        if text.startswith("```"):
            lines = text.split("\n")
            # убираем первую строку (```json или ```) и последнюю (```)
            inner = "\n".join(lines[1:])
            if inner.endswith("```"):
                inner = inner[:-3]
            text = inner.strip()

        if not text.startswith("{"):
            return None

        try:
            data = json.loads(text)
            if "type" in data:
                return data
        except json.JSONDecodeError:
            pass

        return None