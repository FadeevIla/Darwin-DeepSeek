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
        chat = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Код:\n\n{code}"},
            ],
            model="deepseek-chat",  # DeepSeek V4 Flash
            temperature=temperature,
            max_tokens=4000,
        )
        return self._clean(chat.choices[0].message.content)

    @staticmethod
    def _clean(raw):
        cleaned = raw.strip()
        # Убираем markdown
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        # Убираем пояснения в начале ("Вот исправленный код:", "Here is the fixed code:")
        lines = cleaned.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ", "#!", "#!/")):
                return "\n".join(lines[i:])
            if not line.strip() or line.strip().startswith(("Вот", "Here", "Конечно", "Sure", "```")):
                continue
            break
        return cleaned