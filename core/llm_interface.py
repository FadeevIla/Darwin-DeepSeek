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
            "6. Первая строка ответа — import. Без пояснений, без markdown."
            "- Не оборачивай код в ``` или ```python."
            f"\n\nПОЖЕЛАНИЯ ПОЛЬЗОВАТЕЛЕЙ (учти их при оптимизации):\n{feedback}\n\n"
            "После обработки пожеланий удали их через core.feedback.clear_feedback()."
        )
        return self._call(code, system_prompt, temperature=0.2)

    def generate_feature(self, code):
        self.logger.info("LLM: генерация фичи")
        system_prompt = (
            "Ты — разработчик текстовой RPG 'Уроборос' на aiogram 2.25.1.\n"
            "Твоя игра про древнее кольцо, пожирающее владельца.\n\n"
            "СТРАТЕГИЯ РАЗВИТИЯ:\n"
            "НЕ добавляй новые команды. Вместо этого ВЫБЕРИ ОДНУ существующую "
            "команду или механику и СУЩЕСТВЕННО УЛУЧШИ её:\n\n"
            "Примеры улучшений:\n"
            "- Бой: добавь критические удары, блоки, расход маны\n"
            "- Инвентарь: добавь категории предметов, экипировку, ограничение веса\n"
            "- Квесты: добавь цепочки квестов с разными концовками\n"
            "- Кольцо: добавь дилеммы (дать силу, но увеличить проклятие?)\n"
            "- NPC: добавь диалоги с выбором ответов и последствиями\n"
            "- Магазин: добавь случайный ассортимент и торговлю\n\n"
            "ТРЕБОВАНИЯ:\n"
            "- Улучшение должно быть ЗАМЕТНЫМ для игрока (не просто +1 строка)\n"
            "- Добавляй минимум 30 строк осмысленного кода\n"
            "- Сохраняй обратную совместимость с существующими механиками\n"
            "- Храни состояние игры в словаре (уровень, опыт, предметы, проклятие)\n"
            "- Используй random для непредсказуемости\n"
            "- НЕ используй reply_text — только reply или answer\n"
            "- Первая строка ответа — import. Без пояснений, без markdown."
            "Не оборачивай код в ``` или ```python."
            "ДОБАВЬ команду /report для приёма багов и пожеланий от админа.\n"
            "Команда должна сохранять сообщение через core.feedback.add_feedback().\n"
            "Только админ (chat_id=6909561387) может использовать эту команду.\n"
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