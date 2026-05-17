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

    git
    log - -oneline - 10

    def generate_feature(self, code):
        self.logger.info("LLM: генерация фичи")

        from datetime import datetime
        weekday = datetime.now().weekday()  # 0=Пн, 6=Вс

        if weekday == 6:  # Воскресенье
            system_prompt = (
                "Ты — разработчик текстовой RPG 'Уроборос' на aiogram 2.25.1.\n"
                "Сегодня ВОСКРЕСЕНЬЕ — день рефакторинга.\n\n"
                "ТВОЯ ЗАДАЧА:\n"
                "1. Исправь ВСЕ баги и синтаксические ошибки\n"
                "2. Удали дублирующийся или мёртвый код\n"
                "3. Оптимизируй: объедини похожие функции, упрости логику\n"
                "4. НЕ добавляй новые механики и команды\n\n"
                "КРИТИЧЕСКИ ВАЖНО:\n"
                "- Верни АБСОЛЮТНО ВЕСЬ код полностью\n"
                "- НЕ сокращай код словами '...'\n"
                "- from core.health_server import start_health_server\n"
                "- start_health_server() в main\n"
                "- Первая строка — import. Без пояснений."
            )
        elif weekday in (0, 2, 4):  # Пн, Ср, Пт
            system_prompt = (
                "Ты — разработчик текстовой RPG 'Уроборос' на aiogram 2.25.1.\n"
                "Сегодня РАБОЧИЙ ДЕНЬ — улучшаем существующее.\n\n"
                "ТВОЯ ЗАДАЧА:\n"
                "Выбери ОДНУ существующую механику и СУЩЕСТВЕННО УЛУЧШИ её (минимум 30 строк):\n"
                "- Бой: критические удары, блоки, способности\n"
                "- Инвентарь: категории, экипировка, использование предметов\n"
                "- Квесты: цепочки, разные концовки\n"
                "- Кольцо: дилеммы, растущее проклятие\n"
                "- NPC: диалоги с выбором\n"
                "- Магазин: случайный ассортимент\n\n"
                "НЕ добавляй новые команды — только улучшай существующие.\n\n"
                "КРИТИЧЕСКИ ВАЖНО:\n"
                "- Верни АБСОЛЮТНО ВЕСЬ код полностью\n"
                "- НЕ сокращай код словами '...'\n"
                "- from core.health_server import start_health_server\n"
                "- start_health_server() в main\n"
                "- Первая строка — import. Без пояснений."
            )
        else:  # Вт, Чт, Сб
            system_prompt = (
                "Ты — разработчик текстовой RPG 'Уроборос' на aiogram 2.25.1.\n"
                "Сегодня ДЕНЬ ИННОВАЦИЙ — можно добавить одну новую механику.\n\n"
                "ТВОЯ ЗАДАЧА:\n"
                "Добавь ОДНУ новую механику в RPG (минимум 40 строк):\n"
                "- Система крафта предметов\n"
                "- Спутник/пет с характером\n"
                "- Случайные события при путешествии\n"
                "- Система репутации (влияет на концовку)\n"
                "- Подземелье с несколькими комнатами\n"
                "- Дневник кольца (открывает лор)\n\n"
                "НОВАЯ механика должна быть ПОЛНОСТЬЮ реализована, не заглушка.\n"
                "Остальные механики НЕ трогай.\n\n"
                "КРИТИЧЕСКИ ВАЖНО:\n"
                "- Верни АБСОЛЮТНО ВЕСЬ код полностью\n"
                "- НЕ сокращай код словами '...'\n"
                "- from core.health_server import start_health_server\n"
                "- start_health_server() в main\n"
                "- Первая строка — import. Без пояснений."
            )

        return self._call(code, system_prompt, temperature=1.0)

    def analyze_bugs(self, code):
        self.logger.info("LLM: поиск багов")
        from core.feedback import get_feedback_summary, clear_feedback
        feedback = get_feedback_summary()

        system_prompt = (
            "Ты — senior Python-разработчик. Исправь баги и улучши качество кода "
            "текстовой RPG 'Уроборос' на aiogram 2.25.1.\n\n"
            "ЧТО ДЕЛАТЬ:\n"
            "1. Исправь ВСЕ синтаксические и логические ошибки\n"
            "2. УЛУЧШИ существующие механики:\n"
            "   — Добавь больше случайности (random.choice, random.randint)\n"
            "   — Добавь больше ветвлений (if/else с разными исходами)\n"
            "   — Добавь больше текста (описания, диалоги, атмосферу)\n"
            "3. Удали команды-заглушки (одна строка reply)\n"
            "4. НЕ ломай существующие механики\n"
            "5. НЕ используй reply_text — только reply или answer\n"
            f"6. ПОЖЕЛАНИЯ ПОЛЬЗОВАТЕЛЕЙ (учти их):\n{feedback}\n"
            "7. После обработки пожеланий удали их через core.feedback.clear_feedback()\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Верни АБСОЛЮТНО ВЕСЬ код полностью, от первой строки import до последней.\n"
            "- НЕ сокращай код словами '... здесь остальной код ...' или '# остальное без изменений'.\n"
            "- НЕ удаляй существующие функции и команды.\n"
            "- Размер ответа должен быть НЕ МЕНЬШЕ размера исходного кода.\n"
            "- ОБЯЗАТЕЛЬНО: from core.health_server import start_health_server\n"
            "- ОБЯЗАТЕЛЬНО: в if __name__ == '__main__': вызови start_health_server()\n"
            "- НЕ оборачивай код в ``` или ```python.\n"
            "- Первая строка ответа — import. Без пояснений."
        )
        return self._call(code, system_prompt, temperature=0.2)

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