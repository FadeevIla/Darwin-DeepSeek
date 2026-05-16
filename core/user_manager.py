# core/user_manager.py
"""Управление списком пользователей бота."""
import json
import os

USERS_FILE = "users.json"

def load_users():
    """Загружает список chat_id пользователей."""
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_users(users):
    """Сохраняет список пользователей."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(set(users)), f)  # убираем дубликаты

def add_user(chat_id: int):
    """Добавляет пользователя в список."""
    users = load_users()
    if chat_id not in users:
        users.append(chat_id)
        save_users(users)

def get_all_users():
    """Возвращает список всех chat_id."""
    return load_users()