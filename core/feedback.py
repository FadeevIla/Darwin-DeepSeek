# core/feedback.py
"""Система сбора и хранения обратной связи от админа."""
import json
import os
from datetime import datetime, timezone

FEEDBACK_FILE = "feedback.json"


def load_feedback():
    """Загружает необработанные сообщения."""
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_feedback(messages):
    """Сохраняет список сообщений."""
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def add_feedback(text: str, author: str = "admin"):
    """Добавляет новое сообщение."""
    messages = load_feedback()
    messages.append({
        "text": text,
        "author": author,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    save_feedback(messages)


def get_feedback_summary() -> str:
    """Возвращает сводку для промпта."""
    messages = load_feedback()
    if not messages:
        return "Пожеланий пока нет."

    lines = []
    for msg in messages:
        lines.append(f"- [{msg['author']}] {msg['text']}")
    return "\n".join(lines)


def clear_feedback():
    """Очищает все сообщения."""
    save_feedback([])