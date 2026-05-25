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
            "Ты — senior Python-разработчик. Исправь баги в коде 'Тамагочи-Арены'.\n\n"
            "АРХИТЕКТУРА: монолитный bot.py (все функции в одном файле).\n"
            "Данные хранятся в arena.json через load_arena()/save_arena().\n\n"
            "ИГРОВЫЕ ФУНКЦИИ (которые нужно чинить и улучшать):\n"
            "- start_cmd — приветствие и показ питомца\n"
            "- egg_cmd — получение яйца\n"
            "- incubate_cmd — высиживание яйца (3 раза)\n"
            "- feed_cmd — кормление питомца\n"
            "- train_cmd — тренировка (растут статы, падает голод)\n"
            "- battle_cmd — битва с другим игроком или ботом\n"
            "- top_cmd — таблица лидеров\n"
            "- stats_cmd — статистика питомца\n"
            "- help_cmd — справка\n"
            "- report_cmd — фидбек от админа\n\n"
            "ЧТО ДЕЛАТЬ:\n"
            "1. Найди ВСЕ баги и синтаксические ошибки в КОНКРЕТНОЙ функции\n"
            "2. Верни ТОЛЬКО исправленную функцию ЦЕЛИКОМ (не весь файл!)\n"
            "3. Сохрани сигнатуру (async def, аргументы) и все обращения к arena\n"
            "4. Если функция-заглушка — сделай полноценную с вариативностью\n"
            f"5. ПОЖЕЛАНИЯ ИГРОКОВ (САМОЕ ВАЖНОЕ):\n{feedback}\n"
            "   Внимательно прочитай пожелания. Твоя задача — ИЗМЕНИТЬ КОД так, чтобы игроки увидели разницу.\n"
            "   Если пишут 'бой лёгкий' — добавь врагам силы, критические удары, штрафы от проклятия, random исходы.\n"
            "   Если пишут 'нет разнообразия' — добавь random.choice с минимум 3 разными вариантами.\n"
            "   МЕНЯЙ МЕХАНИКУ, а не просто добавляй текст или шутки.\n"
            "6. НЕ вызывай clear_feedback() — оркестратор сделает это сам.\n\n"
            "7. После обработки: core.feedback.clear_feedback()\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Верни ТОЛЬКО одну функцию (от async def до return/конца)\n"
            "- НЕ меняй другие функции\n"
            "- НЕ оборачивай в ```. Первая строка — async def.\n"
            "- Все HTML-теги валидны (никаких <function>, <bound method>)\n"
            "- Все reply_text замени на reply\n"
            "- НЕ добавляй новые функции без необходимости\n"
            "- Используй load_arena()/save_arena() для работы с данными"
        )
        return self._call(code, system_prompt, temperature=0.2)

    def generate_feature(self, code):
        self.logger.info("LLM: генерация фичи")
        from datetime import datetime
        weekday = datetime.now().weekday()

        base_prompt = (
            "Ты — разработчик игры 'Тамагочи-Арена: Уроборос' на aiogram 2.25.1.\n"
            "Игроки выращивают питомцев из яиц и сражаются на арене.\n\n"
            "АРХИТЕКТУРА: монолитный bot.py (все функции в одном файле).\n"
            "Данные: arena.json через load_arena()/save_arena().\n\n"
            "СУЩЕСТВУЮЩИЕ ФУНКЦИИ (выбери ОДНУ для улучшения):\n"
            "- egg_cmd — получение яйца (простая выдача)\n"
            "- incubate_cmd — высиживание (счётчик до 3)\n"
            "- feed_cmd — кормление (восстанавливает голод/HP/настроение)\n"
            "- train_cmd — тренировка (случайный стат +1-3)\n"
            "- battle_cmd — битва с ботом или игроком (сравнение силы)\n"
            "- top_cmd — таблица лидеров (сортировка по победам)\n"
            "- stats_cmd — статистика питомца\n"
            "- start_cmd — приветствие с информацией о питомце\n\n"
            "ПРАВИЛА УЛУЧШЕНИЯ:\n"
            "- Выбери ОДНУ функцию и СУЩЕСТВЕННО улучши её\n"
            "- Добавь вариативность (random.choice, несколько исходов)\n"
            "- Добавь визуальные эффекты (эмодзи, HTML-форматирование)\n"
            "- Улучшение должно быть заметным игроку (не просто +1 строка)\n"
            "- Минимум 20 строк нового/изменённого кода\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Верни ТОЛЬКО изменённую функцию ЦЕЛИКОМ (не весь файл!)\n"
            "- Сохрани сигнатуру: async def имя(message: types.Message):\n"
            "- Сохрани работу с arena: load_arena()/save_arena()\n"
            "- НЕ ломай другие функции\n"
            "- НЕ меняй register_message_handler\n"
            "- НЕ оборачивай в ```. Первая строка — async def.\n"
            "- Все HTML-теги валидны\n"
            "- Заменяй reply_text на reply\n"
            "- НЕ добавляй новые функции (только улучшай существующие)\n\n"
        )

        if weekday == 6:
            system_prompt = base_prompt + (
                "ВОСКРЕСЕНЬЕ — рефакторинг.\n"
                "Выбери функцию с багами и исправь их.\n"
                "Улучши читаемость кода, добавь комментарии.\n"
                "Верни ТОЛЬКО исправленную функцию."
            )
        elif weekday in (0, 2, 4):
            system_prompt = base_prompt + (
                "ПОНЕДЕЛЬНИК/СРЕДА/ПЯТНИЦА — улучшение.\n"
                "Выбери функцию, которая кажется самой скучной, и СДЕЛАЙ ЕЁ ИНТЕРЕСНОЙ.\n"
                "Добавь: случайные события, разные исходы, эмодзи, юмор.\n"
                "Верни ТОЛЬКО улучшенную функцию."
            )
        else:
            system_prompt = base_prompt + (
                "ВТОРНИК/ЧЕТВЕРГ/СУББОТА — углубление.\n"
                "Выбери функцию и добавь в неё НОВУЮ МЕХАНИКУ.\n"
                "Например: в battle добавь магические способности, в feed — отравление,\n"
                "в train — мини-игру (угадай число для бонуса).\n"
                "Верни ТОЛЬКО улучшенную функцию."
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
                            {"role": "user", "content": f"Функция для улучшения:\n\n{code}"},
                        ],
                        temperature=temperature,
                        max_tokens=3000,
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
            if line.strip().startswith(("async def ", "def ", "import ", "from ")):
                return "\n".join(lines[i:])
        return "\n".join(lines)