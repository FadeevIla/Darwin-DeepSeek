# core/feedback.py
"""Система сбора и хранения обратной связи с пушем в GitHub."""
import json
import os
import base64
import requests
from datetime import datetime, timezone

FEEDBACK_FILE = "feedback.json"

# Настройки GitHub (должны быть в переменных окружения на Render)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_NAME = os.environ.get("REPO_NAME", "FadeevIla/Darwin-DeepSeek")

def load_feedback():
    """Загружает сообщения из локального файла."""
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_feedback(messages):
    """Сохраняет сообщения локально."""
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def _push_to_github(messages: list):
    """Пушит feedback.json в GitHub репозиторий."""
    if not GITHUB_TOKEN or not REPO_NAME:
        print("⚠️ GITHUB_TOKEN или REPO_NAME не заданы — фидбек не будет запушен")
        return
    
    try:
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/feedback.json"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }
        
        # Получаем текущий SHA файла (если он есть)
        resp = requests.get(url, headers=headers)
        sha = ""
        if resp.status_code == 200:
            sha = resp.json().get("sha", "")
        elif resp.status_code == 404:
            pass  # Файла ещё нет — создадим
        else:
            print(f"⚠️ Ошибка доступа к GitHub: {resp.status_code} {resp.text[:100]}")
            return
        
        # Кодируем и пушим
        content = json.dumps(messages, ensure_ascii=False, indent=2)
        content_base64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        
        data = {
            "message": "📝 Обновлён feedback.json",
            "content": content_base64,
        }
        if sha:
            data["sha"] = sha
        
        resp = requests.put(url, headers=headers, json=data)
        if resp.status_code in (200, 201):
            print("✅ feedback.json запушен в GitHub")
        else:
            print(f"⚠️ Ошибка пуша: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"⚠️ Ошибка при пуше фидбека: {e}")

def add_feedback(text: str = "", author: str = "system", **kwargs):
    """
    Добавляет сообщение в фидбек и пушит в GitHub.
    Принимает text и author как основные аргументы.
    Любые другие аргументы (user_id, command, и т.д.) сохраняются в details.
    """
    messages = load_feedback()
    
    entry = {
        "text": str(text) if text else str(kwargs.get("command", "фидбек")),
        "author": str(author),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Сохраняем дополнительные данные
    if kwargs:
        entry["details"] = {k: str(v) for k, v in kwargs.items()}
    
    messages.append(entry)
    save_feedback(messages)
    _push_to_github(messages)  # 🆕 Пушим в GitHub

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