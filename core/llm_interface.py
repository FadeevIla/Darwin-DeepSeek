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
            "АРХИТЕКТУРА (актуальная):\n"
            "- bot.py — регистрация команд в register_handlers(dp) + НОВЫЕ команды\n"
            "- core/rpg_player.py — игрок (характеристики, уровень)\n"
            "- core/rpg_combat.py — бой (attack_turn, get_random_enemy, fight_result)\n"
            "- core/rpg_shop.py — магазин (get_shop_list, buy_item)\n"
            "- core/rpg_inventory.py — инвентарь\n"
            "- core/rpg_events.py — отдых (rest) + explore_event\n"
            "- core/rpg_quests.py — квесты (get_quest_log, complete_quest_step, get_quest_reward)\n"
            "- core/rpg_help.py — START_MESSAGE, HELP_MESSAGE, get_help_text\n"
            "- core/feedback.py — фидбек (add_feedback, clear_feedback, get_feedback_count)\n\n"
            "ПРИ ДОБАВЛЕНИИ НОВЫХ КОМАНД ВСЕГДА ОБНОВЛЯЙ:\n"
            "1. rpg_help.py → HELP_MESSAGE (добавь описание новой команды)\n"
            "2. rpg_help.py → START_MESSAGE (если нужно)\n"
            "3. bot.py → register_handlers (регистрация команды)\n"
            "4. bot.py → импорты (если новый модуль)\n\n"
            "ЧТО ДЕЛАТЬ:\n"
            "1. Найди ВСЕ баги и синтаксические ошибки\n"
            "2. Верни ИСПРАВЛЕННЫЙ файл ЦЕЛИКОМ\n"
            "3. Если команда-заглушка — сделай полноценную\n"
            f"4. ПОЖЕЛАНИЯ: {feedback}\n"
            "5. После обработки: core.feedback.clear_feedback()\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Верни ТОЛЬКО изменённый файл ЦЕЛИКОМ\n"
            "- НЕ оборачивай в ```. Первая строка — import.\n"
            "- НЕ сокращай код.\n"
            "- ВСЕ HTML-теги должны быть валидными (никаких <function>, <bound method>)"
        )
        return self._call(code, system_prompt, temperature=0.2)

    def generate_feature(self, code):
        self.logger.info("LLM: генерация фичи")
        from datetime import datetime
        weekday = datetime.now().weekday()

        base_prompt = (
            "Ты — разработчик RPG 'Уроборос' на aiogram 2.25.1.\n\n"
            "АРХИТЕКТУРА (актуальная):\n"
            "- bot.py — регистрация команд в register_handlers(dp)\n"
            "- core/rpg_player.py — игрок\n"
            "- core/rpg_combat.py — бой (attack_turn)\n"
            "- core/rpg_shop.py — магазин\n"
            "- core/rpg_inventory.py — инвентарь\n"
            "- core/rpg_events.py — отдых, explore_event\n"
            "- core/rpg_quests.py — квесты\n"
            "- core/rpg_help.py — START_MESSAGE, HELP_MESSAGE, get_help_text\n"
            "- core/feedback.py — фидбек\n\n"
            "ПРИ ДОБАВЛЕНИИ НОВЫХ КОМАНД ВСЕГДА ОБНОВЛЯЙ:\n"
            "1. rpg_help.py → HELP_MESSAGE (добавь описание новой команды)\n"
            "2. rpg_help.py → START_MESSAGE (если нужно)\n"
            "3. bot.py → register_handlers (регистрация команды)\n"
            "4. bot.py → импорты (если новый модуль)\n\n"
            "ПРАВИЛА:\n"
            "- НОВАЯ механика → новый файл core/rpg_NAME.py + обнови bot.py И rpg_help.py\n"
            "- УЛУЧШЕНИЕ → меняй ТОЛЬКО один модуль\n"
            "- ВСЕГДА возвращай изменённый файл ЦЕЛИКОМ\n"
            "- НЕ оборачивай в ```. Первая строка — import.\n"
            "- НЕ сокращай код.\n"
            "- ВСЕ HTML-теги валидны (никаких <function>)\n"
            "- from core.health_server import start_health_server ВСЕГДА в bot.py\n"
            "- start_health_server() ВСЕГДА в main\n\n"
        )

        if weekday == 6:
            system_prompt = base_prompt + (
                "ВОСКРЕСЕНЬЕ — рефакторинг.\n"
                "Исправь ВСЕ баги. Удали мёртвый код. Оптимизируй.\n"
                "Верни ИСПРАВЛЕННЫЙ файл ЦЕЛИКОМ.\n"
                "НЕ добавляй новые механики."
            )
        elif weekday in (0, 2, 4):
            system_prompt = base_prompt + (
                "ПОНЕДЕЛЬНИК/СРЕДА/ПЯТНИЦА — улучшение.\n"
                "Выбери ОДИН модуль и СУЩЕСТВЕННО улучши его (минимум 30 строк).\n"
                "Верни изменённый модуль ЦЕЛИКОМ.\n"
                "НЕ создавай новые файлы."
            )
        else:
            system_prompt = base_prompt + (
                "ВТОРНИК/ЧЕТВЕРГ/СУББОТА — инновация.\n"
                "Создай ОДИН новый модуль core/rpg_NAME.py с НОВОЙ механикой (минимум 40 строк).\n"
                "Обнови bot.py: импорт + register_handlers.\n"
                "Обнови rpg_help.py: добавь команду в HELP_MESSAGE.\n"
                "Верни: (1) НОВЫЙ модуль, (2) bot.py, (3) rpg_help.py.\n"
                "Раздели ответ метками: ###MODULE###, ###BOT_PY###, ###HELP###"
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