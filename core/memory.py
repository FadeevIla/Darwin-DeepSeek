# core/memory.py
"""Управление памятью фич и коммитов."""
import os
import json
import hashlib
from datetime import datetime, timezone


class Memory:
    def __init__(self, memory_file, logger):
        self.memory_file = memory_file
        self.logger = logger
        self.data = self._load()

    def _load(self):
        if not os.path.exists(self.memory_file):
            self.logger.info("Файл памяти не найден, создаю новый")
            return {"features": [], "commit_history": []}

        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.logger.debug(f"Память загружена: {len(data['features'])} фич")
            return data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(f"Ошибка чтения памяти: {e}")
            return {"features": [], "commit_history": []}

    def save(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            self.logger.debug("Память сохранена")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения памяти: {e}")

    def is_duplicate(self, code, threshold=0.7):
        new_hash = hashlib.sha256(code.encode()).hexdigest()

        for entry in self.data["features"]:
            if entry["code_hash"] == new_hash:
                return True, "exact_match"

            old_lines = set(entry.get("preview", "").split("\n"))
            new_lines = set(code.split("\n"))
            if len(old_lines) > 10 and len(new_lines) > 10:
                intersection = old_lines & new_lines
                similarity = len(intersection) / max(len(old_lines), len(new_lines))
                if similarity > threshold:
                    return True, f"similar ({similarity:.0%})"

        return False, ""

    def add_feature(self, code, feature_type):
        entry = {
            "code_hash": hashlib.sha256(code.encode()).hexdigest(),
            "type": feature_type,
            "date": datetime.now(timezone.utc).isoformat(),
            "preview": "\n".join(code.split("\n")[:30])
        }
        self.data["features"].append(entry)
        if len(self.data["features"]) > 50:
            self.data["features"] = self.data["features"][-50:]
        self.save()
        self.logger.info(f"Запомнена фича: type={feature_type}, hash={entry['code_hash'][:12]}")

    def add_commit(self, sha, message):
        entry = {
            "sha": sha,
            "message": message,
            "date": datetime.now(timezone.utc).isoformat()
        }
        self.data["commit_history"].append(entry)
        if len(self.data["commit_history"]) > 20:
            self.data["commit_history"] = self.data["commit_history"][-20:]
        self.save()
        self.logger.info(f"Запомнен коммит: {sha[:7]}")