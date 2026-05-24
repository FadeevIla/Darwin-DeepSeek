# self_fixing_bot.py — ОРКЕСТРАТОР (НЕ трогается LLM)
"""
Дарвин — бот, который сам себя улучшает.
Оркестратор цикла самосовершенствования.

Этот файл НЕ редактируется нейросетью.
LLM имеет доступ только к bot.py.
"""
import os
import sys
import time
import random
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

# 🔧 Автозагрузка .env файла
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print("✅ .env файл загружен")
except ImportError:
    print("ℹ️  python-dotenv не установлен, .env не загружается")
    print("   Установи: pip install python-dotenv")

# Добавляем корень в path
sys.path.insert(0, str(Path(__file__).parent))

from core.config import load_config
from core.logger import setup_logging
from core.notifier import Notifier
from core.memory import Memory
from core.validator import Validator
from core.github_ops import GitHubOps
from core.llm_interface import LLMInterface
from github import InputGitTreeElement


class DarwinOrchestrator:
    """Оркестратор цикла самосовершенствования."""

    def __init__(self):
        # Загружаем конфиг
        self.config = load_config()

        # Настраиваем логирование
        self.logger, self.event_logger = setup_logging()
        self.logger.info("=" * 50)
        self.logger.info("ДАРВИН: Оркестратор инициализируется")
        self.logger.info("=" * 50)

        # Уведомления
        self.notifier = Notifier(
            self.config["TG_BOT_TOKEN"],
            self.config["TG_CHAT_ID"],
            self.logger
        )

        # Память
        self.memory = Memory(self.config["MEMORY_FILE"], self.logger)

        # Создаём users.json, если его нет
        if not os.path.exists("users.json"):
            with open("users.json", "w", encoding="utf-8") as f:
                json.dump([], f)

        # LLM интерфейс
        self.llm = LLMInterface(
            self.config["DEEPSEEK_API_KEY"],
            self.logger,
            self.notifier
        )

        # Валидатор
        self.validator = Validator(
            self.llm.client,
            self.logger,
            self.notifier
        )

        # GitHub операции
        self.github = GitHubOps(
            self.config["GITHUB_TOKEN"],
            self.config["REPO_NAME"],
            self.config["BOT_FILE_PATH"],
            self.logger,
            self.notifier
        )

        self.logger.info("✅ Оркестратор готов")
        self.notifier.send(
            "🤖 <b>Дарвин запущен</b>\n"
            f"📁 Репозиторий: <code>{self.config['REPO_NAME']}</code>\n"
            f"📄 Целевой файл: <code>{self.config['BOT_FILE_PATH']}</code>\n"
            f"🧠 Память: {len(self.memory.data['features'])} фич",
            "heartbeat"
        )

    def _sync_feedback(self):
        """Сохраняет feedback.json в репозиторий (если есть локальные изменения)."""
        import json

        if not os.path.exists("feedback.json"):
            return

        with open("feedback.json", "r", encoding="utf-8") as f:
            local_feedback = json.load(f)

        if not local_feedback:
            return

        # Пушим в репозиторий
        try:
            content = json.dumps(local_feedback, ensure_ascii=False, indent=2)
            blob = self.github.repo.create_git_blob(content, "utf-8")
            ref = self.github.repo.get_git_ref("heads/main")
            base_commit = self.github.repo.get_git_commit(ref.object.sha)

            element = InputGitTreeElement(
                path="feedback.json",
                mode='100644',
                type='blob',
                sha=blob.sha
            )

            new_tree = self.github.repo.create_git_tree([element], base_commit.tree)
            new_commit = self.github.repo.create_git_commit(
                message="📝 Обновлён feedback.json с сервера",
                tree=new_tree,
                parents=[base_commit]
            )
            ref.edit(sha=new_commit.sha)
            self.logger.info("📝 feedback.json запушен в репозиторий")
        except Exception as e:
            self.logger.warning(f"Не удалось запушить feedback.json: {e}")

    def _describe_changes(self, old_code: str, new_code: str) -> str:
        """Просит LLM описать изменения понятным языком."""
        try:
            old_lines = old_code.split("\n")
            new_lines = new_code.split("\n")

            added = [l for l in new_lines if l not in old_lines]
            removed = [l for l in old_lines if l not in new_lines]

            diff_text = "Добавлено:\n" + "\n".join(added[:15]) + "\n\nУдалено:\n" + "\n".join(removed[:5])

            prompt = (
                "Ты — дружелюбный бот Дарвин. Опиши ОДНИМ предложением на русском, "
                "какую новую функцию ты добавил в свой код или какой баг исправил. "
                "Пиши от первого лица, весело и кратко. "
                "Примеры:\n"
                "- 'Добавил команду /joke — теперь я умею шутить!'\n"
                "- 'Исправил баг с командой /start — она снова работает!'\n"
                "- 'Научился показывать погоду по команде /weather!'\n"
                "Только описание, ничего лишнего."
            )

            # Используем DeepSeek (основная и запасная)
            models = [
                "deepseek-chat",  # DeepSeek V4 Flash
                "deepseek-reasoner",  # DeepSeek R1 (запасная)
            ]

            description = None
            last_error = None

            for model in models:
                try:
                    self.logger.info(f"Описание: пробую модель {model}")
                    chat = self.llm.client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": f"Изменения в коде:\n{diff_text[:1500]}"}
                        ],
                        model=model,
                        temperature=0.8,
                        max_tokens=100,
                    )
                    description = chat.choices[0].message.content.strip()
                    if description:
                        self.logger.info(f"Описание получено от {model}: {description}")
                        break
                except Exception as e:
                    last_error = e
                    self.logger.warning(f"Модель {model} не ответила: {str(e)[:100]}")
                    import time
                    time.sleep(5)
                    continue

            if description:
                return description
            else:
                self.logger.warning(f"Все модели недоступны для описания. Последняя ошибка: {last_error}")
                return "Добавил новую функцию! Попробуй /help, чтобы узнать, что изменилось 🧬"

        except Exception as e:
            self.logger.warning(f"Не удалось сгенерировать описание: {e}")
            return "Добавил новую функцию! Попробуй /help, чтобы узнать, что изменилось 🧬"

    def _save_update_description(self, description: str, commit_sha: str):
        """Сохраняет описание в файл и пушит в репозиторий."""
        update_info = {
            "description": description,
            "commit": commit_sha,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": len(self.memory.data["features"])
        }

        try:
            content = json.dumps(update_info, ensure_ascii=False, indent=2)

            blob = self.github.repo.create_git_blob(content, "utf-8")
            ref = self.github.repo.get_git_ref("heads/main")
            base_commit = self.github.repo.get_git_commit(ref.object.sha)

            element = InputGitTreeElement(
                path="last_update.json",
                mode='100644',
                type='blob',
                sha=blob.sha
            )

            new_tree = self.github.repo.create_git_tree([element], base_commit.tree)
            new_commit = self.github.repo.create_git_commit(
                message="📝 Обновлено описание изменений",
                tree=new_tree,
                parents=[base_commit]
            )
            ref.edit(sha=new_commit.sha)
            self.logger.info(f"📝 Описание сохранено: {description}")
        except Exception as e:
            self.logger.warning(f"Не удалось сохранить описание: {e}")

    def run_cycle(self):
        """Один полный цикл самосовершенствования."""
        cycle_start = datetime.now(timezone.utc)
        self.logger.info("#" * 60)
        self.logger.info(f"ЦИКЛ НАЧАТ: {cycle_start.isoformat()}")
        self.logger.info("#" * 60)

        self.notifier.send(
            f"🔄 Цикл запущен\n"
            f"⏱️ {cycle_start.strftime('%H:%M:%S UTC')}\n"
            f"🧠 Память: {len(self.memory.data['features'])} фич",
            "heartbeat"
        )

        stats = {"bugs_fixed": False, "feature_added": False, "errors": []}

        # --- Шаг 1: Загрузка кода ---
        try:
            self.notifier.send("📥 Загрузка кода из репозитория...", "info")
            code, sha = self.github.get_code()
        except Exception as e:
            self.logger.critical(f"Ошибка загрузки: {e}")
            self.notifier.send(f"💥 Критическая ошибка загрузки: {str(e)[:200]}", "error")
            return False

        # Синхронизируем feedback.json с репозиторием
        try:
            self._sync_feedback()
        except Exception as e:
            self.logger.warning(f"Не удалось синхронизировать фидбек: {e}")

        # --- Шаг 2: Поиск и исправление багов ---
        try:
            self.notifier.send("🔍 Поиск багов через LLM...", "info")
            fixed_code = self.llm.analyze_bugs(code)

            if fixed_code != code:
                self.logger.info(f"Найдены изменения: {abs(len(fixed_code) - len(code))} байт")
                self.notifier.send(
                    f"🐛 Найдены баги\nРазница: {abs(len(fixed_code) - len(code))} байт",
                    "fix"
                )

                is_dup, reason = self.memory.is_duplicate(fixed_code)
                if is_dup:
                    self.logger.info(f"Пропуск: дубликат ({reason})")
                    self.notifier.send(f"⏭️ Фикс пропущен: {reason}", "warning")
                else:
                    valid, validated_code, err = self.validator.full_validation(fixed_code)
                    if valid:
                        commit_msg = "🤖 Auto-fix: нейросеть исправила баги"
                        commit_sha = self.github.push(validated_code, sha, commit_msg)
                        self.memory.add_feature(validated_code, "fix")
                        self.memory.add_commit(commit_sha, "Auto-fix")
                        stats["bugs_fixed"] = True

                        # Генерируем описание исправления
                        description = self._describe_changes(code, validated_code)
                        self._save_update_description(description, commit_sha)
                        self.notifier.send(f"🐛 {description}", "fix")

                        # Синхронизируем зависимости
                        deps_updated, new_reqs = self._sync_dependencies(validated_code)
                        if deps_updated:
                            self._push_requirements(new_reqs)

                        code, sha = validated_code, commit_sha
                    else:
                        stats["errors"].append(f"Валидация фикса: {err}")
            else:
                self.logger.info("Багов не найдено")
                self.notifier.send("✅ Код чист, багов нет", "success")
        except Exception as e:
            self.logger.error(f"Ошибка этапа фикса: {e}")
            stats["errors"].append(f"Фикс: {e}")

        # --- Шаг 3: Генерация новой фичи ---
        try:
            self.notifier.send("💡 Генерация новой фичи...", "info")

            if random.random() > 0.8:
                self.logger.info("Пропуск этапа фич (отдых)")
                self.notifier.send("😴 Бот решил отдохнуть, фичи пропущены", "info")
            else:
                new_code = self.llm.generate_feature(code)

                if new_code != code:
                    self.logger.info(f"Фича сгенерирована: разница {abs(len(new_code) - len(code))} байт")
                    self.notifier.send(
                        f"✨ Новая фича готова\nРазница: {abs(len(new_code) - len(code))} байт",
                        "feature"
                    )

                    is_dup, reason = self.memory.is_duplicate(new_code)
                    if is_dup:
                        self.logger.info(f"Дубликат фичи: {reason}")
                        self.notifier.send(f"⏭️ Фича пропущена: {reason}", "warning")
                    else:
                        valid, validated_code, err = self.validator.full_validation(new_code)
                        if valid:
                            commit_msg = "🤖 Auto-feature: нейросеть добавила новую функцию"
                            commit_sha = self.github.push(validated_code, sha, commit_msg)
                            self.memory.add_feature(validated_code, "feature")
                            self.memory.add_commit(commit_sha, "Auto-feature")
                            stats["feature_added"] = True

                            # Генерируем описание новой фичи
                            description = self._describe_changes(code, validated_code)
                            self._save_update_description(description, commit_sha)
                            self.notifier.send(f"✨ {description}", "feature")

                            # Синхронизируем зависимости
                            deps_updated, new_reqs = self._sync_dependencies(validated_code)
                            if deps_updated:
                                self._push_requirements(new_reqs)

                            code, sha = validated_code, commit_sha
                        else:
                            stats["errors"].append(f"Валидация фичи: {err}")
                else:
                    self.logger.info("LLM не предложила новой фичи")
                    self.notifier.send("🤔 Нейросеть не придумала новую фичу", "info")
        except Exception as e:
            self.logger.error(f"Ошибка этапа фичи: {e}")
            stats["errors"].append(f"Фича: {e}")

        # --- Итоги ---
        duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        self.logger.info("=" * 60)
        self.logger.info(f"ЦИКЛ ЗАВЕРШЁН: {duration:.1f} сек")
        self.logger.info(f"Баги: {stats['bugs_fixed']} | Фичи: {stats['feature_added']} | Ошибки: {len(stats['errors'])}")
        self.logger.info("=" * 60)

        summary = [
            f"⏱️ Длительность: {duration:.1f} сек",
            f"🐛 Баги: {'исправлены' if stats['bugs_fixed'] else 'нет'}",
            f"✨ Фичи: {'добавлены' if stats['feature_added'] else 'нет'}",
        ]
        if stats["errors"]:
            summary.append(f"⚠️ Ошибок: {len(stats['errors'])}")

        level = "success" if not stats["errors"] else "warning"
        self.notifier.send("\n".join(summary), level)

        return len(stats["errors"]) == 0

    def _push_requirements(self, content: str):
        """Пушит обновлённый requirements.txt в репозиторий."""
        try:
            blob = self.github.repo.create_git_blob(content, "utf-8")
            ref = self.github.repo.get_git_ref("heads/main")
            base_commit = self.github.repo.get_git_commit(ref.object.sha)
            element = InputGitTreeElement(
                path="requirements.txt",
                mode='100644',
                type='blob',
                sha=blob.sha
            )
            new_tree = self.github.repo.create_git_tree([element], base_commit.tree)
            new_commit = self.github.repo.create_git_commit(
                message="📦 Автообновление зависимостей",
                tree=new_tree,
                parents=[base_commit]
            )
            ref.edit(sha=new_commit.sha)
            self.logger.info("📦 requirements.txt обновлён и запушен")
        except Exception as e:
            self.logger.warning(f"Не удалось запушить requirements.txt: {e}")

    def _sync_dependencies(self, code: str):
        """Анализирует импорты в коде и обновляет requirements.txt при необходимости."""
        import re
        import ast

        # Библиотеки, которые гарантированно установлены (стандартная библиотека Python)
        std_libs = {
            'os', 'sys', 'time', 'json', 're', 'random', 'asyncio', 'logging',
            'pathlib', 'datetime', 'traceback', 'tempfile', 'hashlib', 'base64',
            'subprocess', 'secrets', 'importlib', 'typing', 'io', 'collections',
            'functools', 'itertools', 'math', 'string', 'textwrap', 'urllib',
        }

        # Библиотеки, которые мы точно знаем, что нужны (ядро)
        always_needed = {
            'PyGithub', 'openai', 'pyflakes', 'requests', 'python-dotenv',
        }

        # Извлекаем импорты из кода
        imports = set()
        for line in code.split('\n'):
            line = line.strip()
            # import xxx
            if line.startswith('import '):
                parts = line.replace('import ', '').split(',')
                for part in parts:
                    lib = part.strip().split('.')[0].split(' as ')[0].strip()
                    imports.add(lib)
            # from xxx import yyy
            elif line.startswith('from '):
                lib = line.split(' ')[1].split('.')[0].strip()
                imports.add(lib)

        # Определяем, какие библиотеки нужно установить
        # Это эвристика: библиотека не из std_libs → её нужно устанавливать
        needed = set()
        for lib in imports:
            if lib not in std_libs:
                needed.add(lib)

        # Добавляем всегда нужные
        needed = needed | always_needed

        # Сопоставление имён импортов с именами пакетов в PyPI
        pypi_names = {
            'telegram': 'python-telegram-bot',
            'aiogram': 'aiogram==2.25.1',
            'aiohttp': 'aiohttp',
            'dotenv': 'python-dotenv',
            'github': 'PyGithub',
            'groq': 'groq',
            'PIL': 'Pillow',
            'yaml': 'PyYAML',
            'bs4': 'beautifulsoup4',
            'sklearn': 'scikit-learn',
            'cv2': 'opencv-python',
            'numpy': 'numpy',
            'pandas': 'pandas',
            'flask': 'flask',
            'django': 'django',
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn',
        }

        # Формируем список пакетов для requirements.txt
        packages = []
        for lib in sorted(needed):
            # Пропускаем локальные модули проекта
            if lib in ['core', 'utils', 'config', 'bot', 'self_fixing_bot']:
                continue
            packages.append(pypi_names.get(lib, lib))

        # Читаем текущий requirements.txt
        try:
            with open('requirements.txt', 'r') as f:
                current = set(line.strip().split('==')[0].split('>=')[0] for line in f if line.strip())
        except FileNotFoundError:
            current = set()

        # Проверяем, есть ли новые
        current_pkg_names = set()
        for pkg in packages:
            current_pkg_names.add(pkg.split('==')[0].split('>=')[0])

        if current_pkg_names - current:
            # Есть новые зависимости — обновляем requirements.txt
            new_content = '\n'.join(sorted(packages)) + '\n'
            with open('requirements.txt', 'w') as f:
                f.write(new_content)

            self.logger.info(f"📦 Обнаружены новые зависимости: {current_pkg_names - current}")
            return True, new_content
        else:
            self.logger.info("📦 Зависимости актуальны")
            return False, None

    def start(self):
        """Запуск бесконечного цикла."""
        interval = self.config["CYCLE_INTERVAL"]
        cycle = 0

        # Проверка подключений
        try:
            self.github.get_code()
            self.logger.info("✅ Все подключения проверены")
        except Exception as e:
            self.logger.critical(f"Ошибка подключения: {e}")
            self.notifier.send(f"💥 Ошибка запуска: {str(e)[:200]}", "error")
            sys.exit(1)

        try:
            while True:
                cycle += 1
                self.logger.info(f"\n{'#' * 60}\n### ЦИКЛ #{cycle}\n{'#' * 60}")

                try:
                    self.run_cycle()
                except Exception as e:
                    self.logger.critical(f"Ошибка цикла #{cycle}: {e}")
                    self.logger.critical(traceback.format_exc())
                    self.notifier.send(f"💥 Ошибка цикла #{cycle}: {str(e)[:200]}", "error")

                self.logger.info(f"Ожидание {interval} сек...")
                time.sleep(interval)

        except KeyboardInterrupt:
            self.logger.info("Остановлен пользователем")
            self.notifier.send("🛑 Дарвин остановлен вручную", "info")


if __name__ == "__main__":
    orchestrator = DarwinOrchestrator()
    orchestrator.start()