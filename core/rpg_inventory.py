# core/rpg_inventory.py
"""Инвентарь игрока."""

def get_inventory_text(player: dict) -> str:
    """Возвращает текст для отображения инвентаря."""
    inv = player.get("inventory", [])
    if not inv:
        return "🎒 Инвентарь пуст. Сразись с врагами или купи предметы в /shop!"
    return "🎒 <b>Инвентарь</b>\n" + "\n".join(f"• {item}" for item in inv)

def add_item(player: dict, item: str):
    """Добавляет предмет в инвентарь."""
    if "inventory" not in player:
        player["inventory"] = []
    player["inventory"].append(item)

def remove_item(player: dict, item: str) -> bool:
    """Удаляет предмет из инвентаря. Возвращает True если предмет был."""
    if item in player.get("inventory", []):
        player["inventory"].remove(item)
        return True
    return False