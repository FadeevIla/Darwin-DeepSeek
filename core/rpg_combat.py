# core/rpg_combat.py
"""Боевая система RPG 'Уроборос'."""
import random

ENEMIES = [
    {"name": "Теневой волк", "hp": 30, "min_damage": 5, "max_damage": 15, "xp": 30, "coins": 20},
    {"name": "Страж руин", "hp": 50, "min_damage": 10, "max_damage": 20, "xp": 50, "coins": 35},
    {"name": "Дух проклятого", "hp": 40, "min_damage": 15, "max_damage": 25, "xp": 40, "coins": 30},
    {"name": "Гоблин-разбойник", "hp": 25, "min_damage": 3, "max_damage": 10, "xp": 20, "coins": 15},
]


def get_random_enemy():
    """Возвращает случайного врага с небольшим разбросом характеристик."""
    enemy = random.choice(ENEMIES).copy()
    # Случайный разброс ±20%
    enemy["hp"] = int(enemy["hp"] * random.uniform(0.8, 1.2))
    enemy["min_damage"] = int(enemy["min_damage"] * random.uniform(0.8, 1.2))
    enemy["max_damage"] = int(enemy["max_damage"] * random.uniform(0.8, 1.2))
    return enemy


def fight_result(player: dict, enemy: dict) -> dict:
    """
    Проводит один раунд боя.
    Возвращает словарь с результатом: {"win": bool, "crit": bool, "player_damage": int, "enemy_damage": int, "message": str}
    """
    player_damage = random.randint(10, 25) + player["level"] * 2
    enemy_damage = random.randint(enemy["min_damage"], enemy["max_damage"])

    # Критический удар (20% шанс)
    crit = random.random() < 0.2
    if crit:
        player_damage = int(player_damage * 2)

    enemy["hp"] -= player_damage

    if enemy["hp"] <= 0:
        # Победа
        player["xp"] += enemy["xp"]
        player["coins"] += enemy["coins"]
        player["curse"] = min(100, player["curse"] + random.randint(0, 3))

        from core.rpg_player import level_up
        level_up_text = ""
        if level_up(player):
            level_up_text = "\n🎉 Уровень повышен!"

        crit_text = "💥 КРИТИЧЕСКИЙ УДАР! " if crit else ""
        message = (
            f"⚔️ Бой с <b>{enemy['name']}</b>\n\n"
            f"{crit_text}Ты наносишь {player_damage} урона.\n"
            f"Победа!{level_up_text}\n"
            f"Получено: {enemy['xp']} XP, {enemy['coins']} 🪙\n"
            f"🌀 Проклятие: {player['curse']}/100"
        )
        return {"win": True, "crit": crit, "player_damage": player_damage, "enemy_damage": 0, "message": message,
                "enemy": enemy}
    else:
        # Враг выжил
        player["hp"] -= enemy_damage
        message = (
            f"⚔️ Бой с <b>{enemy['name']}</b>\n\n"
            f"Ты наносишь {player_damage} урона, но враг выжил!\n"
            f"Враг наносит {enemy_damage} урона в ответ.\n"
            f"❤️ Твоё HP: {player['hp']}/{player['max_hp']}\n\n"
            f"<i>Продолжай атаковать!</i>"
        )
        return {"win": False, "crit": False, "player_damage": player_damage, "enemy_damage": enemy_damage,
                "message": message, "enemy": enemy}