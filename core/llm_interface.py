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
            "Ты — senior Python-разработчик. Исправь ВСЕ баги в коде телеграм-бота "
            "на aiogram 2.25.1. НЕ используй reply_text — только reply или answer. "
            "Верни ПОЛНЫЙ код без markdown."
        )
        return self._call(code, system_prompt, temperature=0.2)

    def generate_feature(self, code):
        self.logger.info("LLM: генерация фичи")
        system_prompt = (
            "Ты — разработчик телеграм-ботов на aiogram 2.25.1. "
            "Добавь ОДНУ новую ПОЛНОСТЬЮ РАБОЧУЮ команду. "
            "НЕ используй reply_text — только reply или answer. "
            "Верни ПОЛНЫЙ код без markdown."
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
        """Очищает вывод LLM от markdown и пояснений."""
        cleaned = raw.strip()

        # Циклично убираем markdown и пояснения, пока первая строка не станет кодом
        for _ in range(5):  # максимум 5 попыток
            # Убираем открывающие ```python или ```
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = lines[1:]  # убираем первую строку с ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
                continue

            # Убираем одиночные ``` в любой строке
            lines = cleaned.split("\n")
            lines = [l for l in lines if l.strip() != "```"]
            cleaned = "\n".join(lines).strip()

            # Проверяем первую непустую строку
            first_line = ""
            for line in cleaned.split("\n"):
                if line.strip():
                    first_line = line.strip()
                    break

            # Если первая строка — пояснение, убираем его
            if first_line and not first_line.startswith(
                    ("import ", "from ", "#!", "#!/", "async def ", "def ", "class ", "BOT_TOKEN", "logger")):
                # Это пояснение — убираем первую строку
                lines = cleaned.split("\n")
                for i, line in enumerate(lines):
                    if line.strip():
                        # Проверяем, похоже ли на код
                        if line.strip().startswith(
                                ("import ", "from ", "#!", "#!/", "async def ", "def ", "class ", "BOT_TOKEN",
                                 "logger")):
                            cleaned = "\n".join(lines[i:])
                            break
                        elif not line.strip().startswith(
                                ("Вот", "Here", "Конечно", "Sure", "Я", "Исправленный", "Ниже", "Below")):
                            # Неизвестная строка — оставляем как есть
                            break
                        else:
                            # Пояснение — пропускаем
                            continue
                break
            else:
                # Первая строка — код, выходим
                break

        return cleaned