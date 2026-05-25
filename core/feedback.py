# core/feedback.py
"""Система сбора и хранения обратной связи."""
import json
import os
from datetime import datetime, timezone

FEEDBACK_FILE = "feedback.json"

def load_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_feedback(messages):
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def add_feedback(text: str = "", author: str = "system", **kwargs):
    """
    Добавляет сообщение в фидбек.
    Принимает text и author как основные аргументы.
    Любые другие переданные аргументы (user_id, command, и т.д.) будут сохранены в details.
    """
    messages = load_feedback()
    
    entry = {
        "text": str(text) if text else str(kwargs.get("command", "фидбек")),
        "author": str(author),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Сохраняем любые дополнительные данные
    if kwargs:
        entry["details"] = {k: str(v) for k, v in kwargs.items()}
    
    messages.append(entry)
    save_feedback(messages)

def get_feedback_summary() -> str:
    messages = load_feedback()
    if not messages:
        return "Пожеланий пока нет."
    lines = []
    for msg in messages:
        lines.append(f"- [{msg.get('author', '?')}] {msg.get('text', '?')}")
    return "\n".join(lines)

def get_feedback_count() -> int:
    return len(load_feedback())

def clear_feedback():
    save_feedback([])