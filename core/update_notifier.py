# core/update_notifier.py
"""Модуль для чтения и отображения информации об обновлениях."""
import json
import os
from pathlib import Path

LAST_UPDATE_FILE = "last_update.json"


def get_update_description():
    """
    Читает last_update.json и возвращает словарь с информацией.
    Возвращает None, если файла нет.
    """
    if not os.path.exists(LAST_UPDATE_FILE):
        return None

    try:
        with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def format_update_message(update_info: dict) -> str:
    """Форматирует информацию об обновлении в красивое сообщение."""
    if not update_info:
        return "Пока обновлений не было 🦎"

    return (
        f"🧬 <b>Последнее обновление</b>\n"
        f"Версия: {update_info.get('version', '?')}\n"
        f"Коммит: <code>{update_info.get('commit', '?')[:7]}</code>\n"
        f"Когда: {update_info.get('timestamp', '?')[:16]}\n\n"
        f"{update_info.get('description', 'Что-то новенькое!')}\n\n"
        f"<i>Попробуй /help, чтобы увидеть все команды</i>"
    )