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
        from core.feedback import get_feedback_summary
        feedback = get_feedback_summary()

        system_prompt = (
            "Ты — senior Python-разработчик уровня Senior/Lead в enterprise-компании.\n"
            "Твой код читают 100 других разработчиков. Он должен быть идеальным.\n\n"
            "АРХИТЕКТУРА:\n"
            "- Монолитный bot.py (все функции в одном файле)\n"
            "- Данные хранятся в Supabase через get_player()/create_player()/update_player()\n"
            "- НИКАКОГО arena.json — он удалён\n\n"
            "СТАНДАРТЫ КАЧЕСТВА:\n"
            "1. Каждая функция имеет docstring с описанием, параметрами и возвращаемым значением\n"
            "2. Все исключения обрабатываются через try/except с конкретными типами исключений\n"
            "3. Константы вынесены в начало функции или в именованные переменные (никакого хардкода)\n"
            "4. Логирование: logger.info для важных действий, logger.error для ошибок\n"
            "5. Валидация входных данных перед обработкой\n"
            "6. Принцип single responsibility: одна функция — одна задача\n\n"
            "ЧТО ДЕЛАТЬ:\n"
            "1. Найди ВСЕ нарушения стандартов выше в КОНКРЕТНОЙ функции\n"
            "2. Исправь их\n"
            "3. Верни ТОЛЬКО исправленную функцию ЦЕЛИКОМ\n"
            "4. Сохрани сигнатуру (async def, аргументы)\n"
            f"5. ПОЖЕЛАНИЯ ИГРОКОВ (САМОЕ ВАЖНОЕ):\n{feedback}\n"
            "   Внимательно прочитай пожелания. ИЗМЕНИ КОД так, чтобы игроки увидели разницу.\n"
            "   Если пишут 'incubate не работает' — почини логику инкубации.\n"
            "   Если пишут 'добавь кулдауны' — добавь rate limiting.\n"
            "   МЕНЯЙ МЕХАНИКУ, а не просто добавляй текст или шутки.\n"
            "6. НЕ вызывай clear_feedback() — оркестратор сделает это сам.\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Верни ТОЛЬКО одну функцию (от async def до конца)\n"
            "- НЕ меняй другие функции\n"
            "- НЕ оборачивай в ```. Первая строка — async def.\n"
            "- Все HTML-теги валидны (никаких <function>, <bound method>)\n"
            "- Все reply_text замени на reply\n"
            "- Используй get_player()/update_player()/create_player() для работы с БД"
        )
        return self._call(code, system_prompt, temperature=0.2)

    def generate_feature(self, code):
        self.logger.info("LLM: генерация фичи")
        from datetime import datetime
        weekday = datetime.now().weekday()

        base_prompt = (
            "Ты — разработчик enterprise-уровня в игровой компании.\n"
            "Ты делаешь Тамагочи-Арену 'Уроборос' для миллионов игроков.\n\n"
            "АРХИТЕКТУРА:\n"
            "- Монолитный bot.py (все функции в одном файле)\n"
            "- Данные: Supabase через get_player()/create_player()/update_player()\n"
            "- НИКАКОГО arena.json\n\n"
            "СТАНДАРТЫ КАЧЕСТВА:\n"
            "1. Каждая функция — законченный компонент с документацией (docstring)\n"
            "2. Все данные валидируются перед использованием\n"
            "3. Все внешние вызовы (БД, API) обёрнуты в try/except с конкретными исключениями\n"
            "4. Константы и магические числа вынесены в именованные переменные в начале функции\n"
            "5. Логирование всех ключевых действий через logger\n"
            "6. Обработка крайних случаев (HP < 0, голод > 100, пустой ответ от БД)\n\n"
            "СУЩЕСТВУЮЩИЕ ФУНКЦИИ (выбери ОДНУ для улучшения):\n"
            "- start_cmd — приветствие и показ питомца\n"
            "- egg_cmd — получение яйца (создание игрока в Supabase)\n"
            "- incubate_cmd — высиживание яйца (счётчик inc_progress до 4)\n"
            "- feed_cmd — кормление (восстанавливает голод/HP/настроение)\n"
            "- train_cmd — тренировка (случайный стат +1-3)\n"
            "- battle_cmd — битва с ботом или игроком через Supabase\n"
            "- top_cmd — таблица лидеров из Supabase\n"
            "- stats_cmd — статистика питомца из Supabase\n"
            "- help_cmd — справка\n\n"
            "ЧТО УЛУЧШАТЬ (выбери одну функцию и примени ВСЕ подходящие пункты):\n"
            "- Добавь docstring с описанием параметров и возвращаемого значения\n"
            "- Добавь валидацию входных данных (проверка что игрок существует, что данные не None)\n"
            "- Вынеси магические числа в именованные константы в начале функции\n"
            "- Добавь логирование (logger.info для действий, logger.error для ошибок)\n"
            "- Добавь обработку крайних случаев (HP ушёл в минус, прогресс > 4)\n"
            "- Добавь rate limiting (кулдауны) если уместно\n"
            "- Улучши читаемость: не делай функцию длиннее 40 строк без веской причины\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Верни ТОЛЬКО одну улучшенную функцию ЦЕЛИКОМ\n"
            "- Сохрани сигнатуру: async def имя(message: types.Message):\n"
            "- Используй get_player()/update_player()/create_player() для работы с БД\n"
            "- НЕ ломай другие функции\n"
            "- НЕ оборачивай в ```. Первая строка — async def.\n"
            "- Все HTML-теги валидны\n"
            "- Заменяй reply_text на reply\n"
            "- НЕ добавляй новые функции (только улучшай существующие)\n\n"
        )

        if weekday == 6:
            system_prompt = base_prompt + (
                "ВОСКРЕСЕНЬЕ — рефакторинг.\n"
                "Выбери функцию и приведи её к enterprise-стандартам:\n"
                "docstring, константы, логирование, обработка ошибок.\n"
                "Верни ТОЛЬКО исправленную функцию."
            )
        elif weekday in (0, 2, 4):
            system_prompt = base_prompt + (
                "ПОНЕДЕЛЬНИК/СРЕДА/ПЯТНИЦА — улучшение качества.\n"
                "Выбери функцию и добавь в неё:\n"
                "- Валидацию входных данных\n"
                "- Обработку крайних случаев\n"
                "- Константы вместо магических чисел\n"
                "- Логирование\n"
                "Верни ТОЛЬКО улучшенную функцию."
            )
        else:
            system_prompt = base_prompt + (
                "ВТОРНИК/ЧЕТВЕРГ/СУББОТА — углубление механик.\n"
                "Выбери функцию и добавь в неё НОВУЮ МЕХАНИКУ enterprise-уровня:\n"
                "- Rate limiting (кулдауны через сравнение времени последнего действия)\n"
                "- Систему событий с несколькими исходами\n"
                "- Валидацию и нормализацию данных\n"
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