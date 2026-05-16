# core/notifier.py
"""Отправка уведомлений в Telegram."""
import requests


class Notifier:
    def __init__(self, bot_token, chat_id, logger):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.logger = logger
        self.enabled = bool(bot_token and chat_id)

    def send(self, message, level="info"):
        if not self.enabled:
            return

        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "🚨",
            "feature": "✨",
            "fix": "🔧",
            "heartbeat": "💓",
        }

        emoji = emoji_map.get(level, "📌")
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        full_msg = f"{emoji} <b>[Darwin]</b>\n<code>{timestamp}</code>\n{message}"

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.chat_id, "text": full_msg, "parse_mode": "HTML"},
                timeout=10
            )
            if resp.status_code != 200:
                self.logger.warning(f"TG send failed: {resp.text}")
        except Exception as e:
            self.logger.error(f"TG error: {e}")