# core/llm_interface.py
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
        from core.feedback import get_feedback_summary, clear_feedback
        feedback = get_feedback_summary()

        system_prompt = (
            "Ты — senior Python-разработчик. Исправь баги в коде RPG 'Уроборос'.\n\n"
            "АРХИТЕКТУРА:\n"
            "- bot.py — только регистрация команд\n"
            "- core/rpg_player.py — игрок (характеристики, уровень)\n"
            "- core/rpg_combat.py — боевая система\n"
            "- core/rpg_shop.py — магазин\n"
            "- core/rpg_inventory.py — инвентарь\n"
            "- core/rpg_events.py — отдых и события\n"
            "- core/rpg_help.py — тексты справки\n\n"
            "ЧТО ДЕЛАТЬ:\n"
            "1. Найди ВСЕ баги и синтаксические ошибки в КОНКРЕТНОМ модуле\n"
            "2. Верни ИСПРАВЛЕННЫЙ модуль ЦЕЛИКОМ\n"
            "3. УЛУЧШИ механику: больше случайности, больше ветвлений, больше текста\n"
            "4. Если команда-заглушка — сделай полноценную\n"
            f"5. ПОЖЕЛАНИЯ: {feedback}\n"
            "6. После обработки: core.feedback.clear_feedback()\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Верни ТОЛЬКО изменённый файл ЦЕЛИКОМ\n"
            "- Если меняешь bot.py — верни ЕГО целиком\n"
            "- Если меняешь модуль — верни МОДУЛЬ целиком\n"
            "- НЕ оборачивай в ```. Первая строка — import.\n"
            "- НЕ сокращай код."
        )
        return self._call(code, system_prompt, temperature=0.2)

    def generate_feature(self, code):
        self.logger.info("LLM: генерация фичи")
        from datetime import datetime
        weekday = datetime.now().weekday()

        base_prompt = (
            "Ты — разработчик RPG 'Уроборос' на aiogram 2.25.1.\n\n"
            "АРХИТЕКТУРА:\n"
            "- bot.py — только регистрация команд (НЕ добавляй логику в bot.py!)\n"
            "- core/rpg_player.py — игрок\n"
            "- core/rpg_combat.py — бой\n"
            "- core/rpg_shop.py — магазин\n"
            "- core/rpg_inventory.py — инвентарь\n"
            "- core/rpg_events.py — события\n"
            "- core/rpg_help.py — справка\n\n"
            "ПРАВИЛА:\n"
            "- НОВАЯ механика → новый файл core/rpg_NAME.py + обнови bot.py\n"
            "- УЛУЧШЕНИЕ → меняй ТОЛЬКО один существующий модуль\n"
            "- ВСЕГДА возвращай изменённый файл ЦЕЛИКОМ\n"
            "- НЕ оборачивай в ```. Первая строка — import.\n"
            "- НЕ сокращай код.\n"
            "- НЕ трогай другие модули без необходимости.\n"
            "- from core.health_server import start_health_server ВСЕГДА в bot.py\n"
            "- start_health_server() ВСЕГДА в main bot.py\n\n"
        )

        if weekday == 6:
            system_prompt = base_prompt + (
                "ВОСКРЕСЕНЬЕ — рефакторинг.\n"
                "Найди и исправь ВСЕ баги. Удали мёртвый код. Оптимизируй.\n"
                "Верни ИСПРАВЛЕННЫЙ файл (модуль или bot.py) ЦЕЛИКОМ.\n"
                "НЕ добавляй новые механики."
            )
        elif weekday in (0, 2, 4):
            system_prompt = base_prompt + (
                "ПОНЕДЕЛЬНИК/СРЕДА/ПЯТНИЦА — улучшение.\n"
                "Выбери ОДИН модуль и СУЩЕСТВЕННО улучши его (минимум 30 строк).\n"
                "Верни изменённый модуль ЦЕЛИКОМ.\n"
                "НЕ создавай новые файлы. НЕ меняй bot.py без необходимости."
            )
        else:
            system_prompt = base_prompt + (
                "ВТОРНИК/ЧЕТВЕРГ/СУББОТА — инновация.\n"
                "Создай ОДИН новый модуль core/rpg_NAME.py с НОВОЙ механикой (минимум 40 строк).\n"
                "Обнови bot.py: добавь импорт и register_message_handler.\n"
                "Верни: (1) НОВЫЙ модуль ЦЕЛИКОМ, (2) ОБНОВЛЁННЫЙ bot.py ЦЕЛИКОМ.\n"
                "Раздели ответ меткой ###BOT_PY### между модулем и bot.py."
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
                            {"role": "user", "content": f"Файл для изменения:\n\n{code}"},
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
                    if "rate" in str(e).lower():
                        time.sleep(30)
                    else:
                        break

        raise last_error

    @staticmethod
    def _clean(raw):
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        lines = [l for l in cleaned.split("\n") if l.strip() != "```"]
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ", "#!", "async def ", "def ", "class ")):
                return "\n".join(lines[i:])
        return "\n".join(lines)