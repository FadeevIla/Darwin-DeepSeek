# core/config.py
"""Загрузка и проверка переменных окружения с поддержкой .env файла."""
import os
import sys
from pathlib import Path


def _load_dotenv():
    """Загружает .env файл из корня проекта, если он существует."""
    # Ищем корень проекта (где лежит .env)
    project_root = Path(__file__).parent.parent

    # Пробуем найти python-dotenv
    try:
        from dotenv import load_dotenv
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return True
        else:
            # Пробуем .env.local, .env.dev
            for alt in [".env.local", ".env.dev"]:
                alt_path = project_root / alt
                if alt_path.exists():
                    load_dotenv(alt_path)
                    return True
    except ImportError:
        pass

    return False


# Загружаем .env до всего остального
_dotenv_loaded = _load_dotenv()


def load_config():
    """
    Загружает и проверяет все необходимые переменные окружения.
    Работает как с .env файлом, так и с реальными переменными окружения.
    """
    config = {
        # GitHub
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN"),
        "REPO_NAME": os.environ.get("REPO_NAME"),
        "BOT_FILE_PATH": os.environ.get("BOT_FILE_PATH", "bot.py"),

        # Память
        "MEMORY_FILE": os.environ.get("MEMORY_FILE", "feature_memory.json"),

        # LLM
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY"),

        # Telegram бот
        "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN"),

        # Telegram уведомления
        "TG_BOT_TOKEN": os.environ.get("TG_BOT_TOKEN"),
        "TG_CHAT_ID": os.environ.get("TG_CHAT_ID"),

        # Интервал эволюции (секунды)
        "CYCLE_INTERVAL": int(os.environ.get("CYCLE_INTERVAL", "3600")),
    }

    # Проверяем обязательные переменные
    required = {
        "GITHUB_TOKEN": config["GITHUB_TOKEN"],
        "REPO_NAME": config["REPO_NAME"],
        "DEEPSEEK_API_KEY": config["DEEPSEEK_API_KEY"],
    }

    missing = [name for name, val in required.items() if not val]

    if missing:
        print("=" * 60)
        print("❌ ОШИБКА: Отсутствуют обязательные переменные окружения!")
        print("=" * 60)
        print(f"   Не найдены: {', '.join(missing)}")
        print()

        if not _dotenv_loaded:
            print("💡 Совет: Установи python-dotenv и создай .env файл:")
            print("   pip install python-dotenv")
            print("   cp .env.example .env")
            print("   # Затем заполни .env реальными токенами")
        else:
            print("💡 .env файл загружен, но в нём не хватает переменных.")
            print("   Проверь .env файл и убедись, что все поля заполнены.")

        print("=" * 60)
        sys.exit(1)

    # Дополнительные проверки
    config["TG_ENABLED"] = bool(config["TG_BOT_TOKEN"] and config["TG_CHAT_ID"])

    if not config["TG_ENABLED"]:
        print("ℹ️  Telegram-уведомления отключены (не заданы TG_BOT_TOKEN и TG_CHAT_ID)")

    return config