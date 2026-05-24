# core/feedback.py
"""Система сбора и хранения обратной связи."""
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
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_feedback(messages):
    """Сохраняет список сообщений."""
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def add_feedback(text: str, author: str = "admin"):
    """Добавляет сообщение и пушит в GitHub через API."""
    messages = load_feedback()
    messages.append({
        "text": text,
        "author": author,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    save_feedback(messages)

    # Пушим через GitHub API
    try:
        import requests
        token = os.environ.get("GITHUB_TOKEN", "")
        repo = os.environ.get("REPO_NAME", "FadeevIla/Darwin-DeepSeek")

        if token and repo:
            # Получаем текущий SHA файла
            url = f"https://api.github.com/repos/{repo}/contents/feedback.json"
            headers = {"Authorization": f"Bearer {token}"}

            resp = requests.get(url, headers=headers)
            sha = resp.json().get("sha", "") if resp.status_code == 200 else ""

            # Пушим обновление
            import base64
            content_base64 = base64.b64encode(json.dumps(messages, ensure_ascii=False, indent=2).encode()).decode()

            data = {
                "message": "📝 Обновлён feedback.json",
                "content": content_base64,
            }
            if sha:
                data["sha"] = sha

            requests.put(url, headers=headers, json=data)
    except Exception:
        pass

    # 🆕 Пушим feedback.json в GitHub (через git)
    _push_feedback_to_github()


def _push_feedback_to_github():
    """Пушит feedback.json в GitHub репозиторий."""
    try:
        import subprocess
        subprocess.run(['git', 'config', '--global', 'user.email', 'darwin@ouroboros.bot'], check=False)
        subprocess.run(['git', 'config', '--global', 'user.name', 'Darwin Bot'], check=False)
        subprocess.run(['git', 'add', 'feedback.json'], check=False)
        subprocess.run(['git', 'commit', '-m', '📝 Обновлён feedback.json'], check=False)
        subprocess.run(['git', 'push'], check=False)
    except Exception:
        pass  # Не страшно, если не получилось (на Render нет прав)


def get_feedback_summary() -> str:
    """Возвращает сводку для промпта."""
    messages = load_feedback()
    if not messages:
        return "Пожеланий пока нет."

    lines = []
    for msg in messages:
        lines.append(f"- [{msg['author']}] {msg['text']}")
    return "\n".join(lines)


def get_feedback_count() -> int:
    """Возвращает количество необработанных сообщений."""
    messages = load_feedback()
    return len(messages)


def clear_feedback():
    """Очищает все сообщения."""
    save_feedback([])