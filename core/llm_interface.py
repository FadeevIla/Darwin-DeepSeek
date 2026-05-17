# core/llm_interface.py (DeepSeek версия)
"""Интерфейс для работы с DeepSeek API."""
from openai import OpenAI

class LLMInterface:
    def __init__(self, api_key, logger, notifier=None):
        self.logger = logger
        self.notifier = notifier
        self.logger.info("Инициализация DeepSeek API")
        self.client = OpenAI(
            base_url="https://api.deepseek.com/v1",
            api_key=api_key,
        )
        self.logger.info("DeepSeek готов")

    def analyze_bugs(self, code):
        self.logger.info("LLM: поиск багов")
        system_prompt = (
            "Ты — senior Python-разработчик. Оптимизируй код текстовой RPG 'Уроборос' на aiogram 2.25.1.\n\n"
            "ПРАВИЛА ОПТИМИЗАЦИИ:\n"
            "1. УДАЛИ команды, которые НЕ являются игровыми механиками и не используются в RPG:\n"
            "   — Критерий: если команда просто возвращает текст-заглушку (один reply) и не взаимодействует с состоянием игры — удали её\n"
            "   — Критерий: если команда не относится к RPG-жанру — удали её\n"
            "2. ОСТАВЬ служебные команды: /start, /help\n"
            "3. ОСТАВЬ игровые механики даже если они простые: /dice, /coinflip, /echo\n"
            "4. ДОБАВЬ одну новую RPG-механику (бой, инвентарь, уровни, квесты, торговец)\n"
            "5. НЕ ломай оставшиеся команды\n"
            "6. НЕ используй reply_text — только reply или answer\n"
            "7. Верни ТОЛЬКО полный код. Первая строка — import. Без пояснений."
            "8. Не оборачивай код в ``` или ```python."
        )
        return self._call(code, system_prompt, temperature=0.2)

    def generate_feature(self, code):
        self.logger.info("LLM: генерация фичи")
        system_prompt = (
            "Ты — разработчик текстовой RPG на aiogram 2.25.1.\n"
            "Твоя игра называется 'Уроборос' — про древнее кольцо, пожирающее владельца.\n\n"
            "ВАЖНО: ты разрабатываешь ОДНУ игру, а не набор команд.\n"
            "Все команды должны быть частью этой RPG.\n\n"
            "Добавь ОДНУ новую механику в игру. Выбери из списка или придумай свою:\n"
            "- Система боя (атака, защита, магия, предметы)\n"
            "- Инвентарь и предметы (зелья, оружие, артефакты)\n"
            "- Система уровней и опыта\n"
            "- Случайные события в путешествии\n"
            "- Влияние кольца (проклятие растёт, даёт бонусы и штрафы)\n"
            "- Торговец или кузнец\n"
            "- Квесты и моральные выборы\n"
            "- Несколько концовок\n\n"
            "ТРЕБОВАНИЯ К КОДУ:\n"
            "- Каждая механика должна быть ГОТОВОЙ К ИСПОЛЬЗОВАНИЮ, а не заглушкой\n"
            "- Храни состояние игры в словаре (уровень, опыт, предметы, проклятие)\n"
            "- Используй random для случайности\n"
            "- Обрабатывай ошибки через try/except\n"
            "- НЕ ломай существующие механики, только дополняй их\n"
            "- НЕ используй reply_text — только reply или answer\n"
            "- Верни ТОЛЬКО полный код. Первая строка — import. Без пояснений."
            "Не оборачивай код в ``` или ```python."
        )
        return self._call(code, system_prompt, temperature=1.0)

    def _call(self, code, system_prompt, temperature):
        import time

        max_code_len = 4000
        if len(code) > max_code_len:
            code = code[:3000] + "\n# ... середина пропущена ...\n" + code[-1000:]

        models = ["deepseek-chat", "deepseek-reasoner"]
        last_error = None

        for model in models:
            for attempt in range(2):
                try:
                    chat = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Код:\n\n{code}"},
                        ],
                        temperature=temperature,
                        max_tokens=4000,
                    )
                    result = self._clean(chat.choices[0].message.content)
                    tokens = chat.usage.total_tokens if hasattr(chat, "usage") else "?"
                    self.logger.info(f"LLM ответ ({model}): {len(result)} символов, {tokens} токенов")
                    return result
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    if "rate" in error_str.lower() or "429" in error_str:
                        wait = 30
                        self.logger.warning(f"Рейт-лимит {model}, жду {wait} сек")
                        time.sleep(wait)
                    else:
                        self.logger.warning(f"Ошибка {model}: {error_str[:100]}")
                        break  # не рейт-лимит — пробуем следующую модель

        self.logger.error(f"Все модели недоступны. Ошибка: {last_error}")
        raise last_error

    @staticmethod
    def _clean(raw):
        """Минимальная очистка вывода LLM."""
        cleaned = raw.strip()

        # На всякий случай убираем ```
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        # Убираем строки, состоящие только из ```
        lines = [l for l in cleaned.split("\n") if l.strip() != "```"]

        return "\n".join(lines)