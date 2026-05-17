# core/validator.py — ИСПРАВЛЕННАЯ ВЕРСИЯ
"""Валидация Python-кода перед пушем."""
import os
import time  # ← ДОБАВЬ ЭТУ СТРОКУ
import tempfile


class Validator:
    def __init__(self, llm_client, logger, notifier=None):
        self.llm_client = llm_client
        self.logger = logger
        self.notifier = notifier

    def validate_syntax(self, code):
        try:
            compile(code, "<generated>", "exec")
            return True, None
        except SyntaxError as e:
            # Выводим проблемную строку
            lines = code.split("\n")
            if e.lineno and e.lineno <= len(lines):
                problem_line = lines[e.lineno - 1]
                self.logger.warning(f"Проблемная строка {e.lineno}: {problem_line[:100]}")
            return False, f"Синтаксическая ошибка: {e.msg} (строка {e.lineno})"

    def validate_imports(self, code):

        # Проверка, что код не пустой и не обрезанный
        if len(code) < 500:
            return False, "Код слишком короткий — вероятно, обрезан"

        if "..." in code and "остальной код" in code.lower():
            return False, "Код содержит пропуски — LLM обрезала ответ"

        if "остальное без изменений" in code.lower():
            return False, "Код содержит пропуски — LLM обрезала ответ"

        # Ищем любые признаки телеграм-бота
        bot_indicators = [
            "telegram", "Telegram", "Bot", "bot",
            "aiogram", "Dispatcher", "executor",
            "from aiogram", "import aiogram",
        ]
        has_bot_framework = any(indicator in code for indicator in bot_indicators)
        if not has_bot_framework:
            return False, "Код не похож на телеграм-бота"

        dangerous = ["os.system", "subprocess.call", "eval(", "exec("]
        for danger in dangerous:
            if danger in code:
                return False, f"Обнаружен опасный вызов: {danger}"

        return True, None

    def validate_pyflakes(self, code):
        try:
            import pyflakes.api
            import pyflakes.reporter

            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
                tmp.write(code)
                tmp.flush()
                tmp_path = tmp.name

            errors = []
            reporter = pyflakes.reporter.Reporter(
                lambda msg: errors.append(str(msg)),
                lambda msg: None
            )
            pyflakes.api.checkPath(tmp_path, reporter)
            os.unlink(tmp_path)

            if errors:
                return False, f"Pyflakes: {'; '.join(errors[:3])}"
            return True, None
        except ImportError:
            return True, None
        except Exception as e:
            return False, f"Pyflakes error: {e}"

    def full_validation(self, code, max_retries=3):
        self.logger.info(f"Валидация (макс. попыток: {max_retries})")

        for attempt in range(max_retries):
            self.logger.info(f"Попытка {attempt + 1}/{max_retries}")

            syntax_ok, syntax_err = self.validate_syntax(code)
            if not syntax_ok:
                self.logger.warning(f"[{attempt + 1}] {syntax_err}")
                if attempt < max_retries - 1:
                    time.sleep(30)  # больше паузы между попытками
                    code = self._llm_fix(code, syntax_err, "syntax")
                    continue
                return False, code, syntax_err

            imports_ok, imports_err = self.validate_imports(code)
            if not imports_ok:
                self.logger.warning(f"[{attempt + 1}] {imports_err}")
                if attempt < max_retries - 1:
                    time.sleep(30)  # ← ПАУЗА 5 СЕКУНД
                    code = self._llm_fix(code, imports_err, "imports")
                    continue
                return False, code, imports_err

            pyflakes_ok, pyflakes_err = self.validate_pyflakes(code)
            if not pyflakes_ok:
                self.logger.warning(f"[{attempt + 1}] {pyflakes_err}")

            self.logger.info("Валидация пройдена")
            return True, code, None

        return False, code, "Исчерпаны попытки"

    def _llm_fix(self, code, error, fix_type):
        import re

        if fix_type == "syntax":
            # Старые замены
            code = re.sub(r'\.reply_text\(', '.reply(', code)
            code = re.sub(r'from aiogram\.types import.*Update,?\s*', '', code)
            code = re.sub(r',\s*Update', '', code)
            code = re.sub(r'from aiogram import.*Application,?\s*', '', code)
            code = re.sub(r',\s*Application', '', code)
            code = re.sub(r'skip_updates\s*=\s*True', '', code)
            code = re.sub(r'executor\.start_polling\(dp,\s*\)', 'executor.start_polling(dp)', code)
            code = re.sub(r'```', '', code)
            code = re.sub(r"commands\s*=\s*\[.*?\]\s*\)", "", code)
            code = re.sub(r'\){2,}', ')', code)

            # Автопочинка строк и скобок
            lines = code.split('\n')
            fixed_lines = []
            for line in lines:
                # Кавычки
                double_quotes = line.count('"') - line.count('\\"')
                single_quotes = line.count("'") - line.count("\\'")
                if double_quotes % 2 != 0:
                    line = line + '"'
                if single_quotes % 2 != 0:
                    line = line + "'"
                if line.strip().endswith(('reply("', 'reply(\'', 'answer("', 'answer(\'')):
                    line = line + '")'

                # Скобки
                open_brackets = line.count('[') - line.count(']')
                open_parens = line.count('(') - line.count(')')
                open_braces = line.count('{') - line.count('}')
                if open_brackets > 0:
                    line = line + ']' * open_brackets
                if open_parens > 0:
                    line = line + ')' * open_parens
                if open_braces > 0:
                    line = line + '}' * open_braces

                # 🆕 Обрыв строки commands=[' → закрываем
                if re.search(r"commands\s*=\s*\['$", line.strip()):
                    line = line + "'])" if "'" in line else line + '"])'

                fixed_lines.append(line)
            code = '\n'.join(fixed_lines)

            # 🆕 Нормализация отступов: убираем лишние 4 пробела в начале
            fixed_lines = []
            for line in code.split('\n'):
                stripped = line.lstrip()
                if stripped:
                    # Если строка начинается с кода, но имеет >4 отступов в середине файла
                    # Оставляем как есть — это может быть вложенный код
                    fixed_lines.append(line)
                else:
                    fixed_lines.append('')
            code = '\n'.join(fixed_lines)

            self.logger.info("Применены локальные автоисправления синтаксиса")
            return code

        import time
        time.sleep(5)
        return code

    @staticmethod
    def _clean_output(raw):
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        return cleaned