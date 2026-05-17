# core/rpg_player.py
"""Управление игроком: создание, характеристики, уровень."""
import random

def init_player():
    """Создаёт нового игрока."""
    return {
        "hp": 100, "max_hp": 100,
        "level": 1, "xp": 0,
        "coins": 50, "curse": 0,
        "inventory": [],
        "weapon": "Кулаки",
        "armor": "Одежда путника",
    }

def get_player(players: dict, user_id: int):
    """Возвращает игрока, создаёт если нет."""
    if user_id not in players:
        players[user_id] = init_player()
    return players[user_id]

def level_up(player: dict) -> bool:
    """Повышает уровень, если достаточно опыта. Возвращает True если уровень повышен."""
    if player["xp"] >= player["level"] * 100:
        player["level"] += 1
        player["xp"] = 0
        player["max_hp"] += 20
        player["hp"] = player["max_hp"]
        return True
    return False