# core/rpg_shop.py
"""Магазин предметов RPG 'Уроборос'."""

SHOP_ITEMS = [
    {"name": "Зелье здоровья", "price": 30, "effect": "heal", "value": 30},
    {"name": "Железный меч", "price": 100, "effect": "weapon", "value": "Железный меч"},
    {"name": "Кожаный доспех", "price": 80, "effect": "armor", "value": "Кожаный доспех"},
]


def get_shop_list():
    """Возвращает список товаров для отображения."""
    return "\n".join(f"• {i['name']} — {i['price']} 🪙" for i in SHOP_ITEMS)


def buy_item(player: dict, item_index: int) -> tuple[bool, str]:
    """
    Покупка предмета. Возвращает (успех, сообщение).
    """
    if item_index < 0 or item_index >= len(SHOP_ITEMS):
        return False, "Такого товара нет."

    item = SHOP_ITEMS[item_index]
    if player["coins"] < item["price"]:
        return False, f"Недостаточно монет! Нужно {item['price']} 🪙, у тебя {player['coins']} 🪙."

    player["coins"] -= item["price"]

    if item["effect"] == "heal":
        player["hp"] = min(player["max_hp"], player["hp"] + item["value"])
        return True, f"Куплено {item['name']}! ❤️ +{item['value']} HP."
    elif item["effect"] == "weapon":
        player["weapon"] = item["value"]
        return True, f"Куплен {item['name']}! ⚔️ Теперь у тебя {item['value']}."
    elif item["effect"] == "armor":
        player["armor"] = item["value"]
        return True, f"Куплен {item['name']}! 🛡️ Теперь у тебя {item['value']}."

    return True, f"Куплено {item['name']}!"