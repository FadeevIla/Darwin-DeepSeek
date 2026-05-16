# core/logger.py
"""Система логирования с ротацией."""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging():
    """Настраивает логирование и возвращает кортеж (main_logger, event_logger)."""
    LOG_DIR = Path("logs")
    LOG_DIR.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Главный логгер
    logger = logging.getLogger("core")
    logger.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        LOG_DIR / "bot.log", maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Логгер событий
    event_logger = logging.getLogger("events")
    event_logger.setLevel(logging.INFO)
    event_handler = RotatingFileHandler(
        LOG_DIR / "events.log", maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    event_handler.setFormatter(formatter)
    event_logger.addHandler(event_handler)

    return logger, event_logger