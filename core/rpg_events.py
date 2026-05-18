# core/rpg_events.py
"""Случайные события и отдых."""
import random

REST_EVENTS = [
    "Ты смотришь на пламя и чувствуешь, как кольцо слегка сжимает палец...",
    "В темноте за костром кто-то наблюдает за тобой.",
    "Тёплый огонь прогоняет холод и страх.",
    "Кольцо шепчет тебе о давно забытых королях...",
    "Где-то вдалеке воет волк. Или не волк.",
]

def explore_event(player: dict) -> str:
    """Случайное событие при исследовании мира."""
    events = [
        {
            "text": "Ты находишь древние руины. Внутри что-то блестит...",
            "coins": random.randint(10, 30),
            "hp_change": 0,
            "curse": random.randint(0, 2),
        },
        {
            "text": "Тёмный лес окружает тебя. Ты слышишь шёпот кольца.",
            "coins": 0,
            "hp_change": -random.randint(5, 15),
            "curse": random.randint(1, 5),
        },
        {
            "text": "Ты встречаешь странствующего торговца.",
            "coins": random.randint(20, 50),
            "hp_change": random.randint(5, 15),
            "curse": 0,
        },
        {
            "text": "Заброшенный храм. Кольцо пульсирует сильнее...",
            "coins": 0,
            "hp_change": 0,
            "curse": random.randint(3, 10),
        },
    ]
    
    event = random.choice(events)
    
    player["coins"] += event["coins"]
    if event["hp_change"] > 0:
        player["hp"] = min(player["max_hp"], player["hp"] + event["hp_change"])
    elif event["hp_change"] < 0:
        player["hp"] += event["hp_change"]  # минус уже есть
    player["curse"] = min(100, player["curse"] + event["curse"])
    
    hp_text = ""
    if event["hp_change"] > 0:
        hp_text = f"\n❤️ +{event['hp_change']} HP"
    elif event["hp_change"] < 0:
        hp_text = f"\n💔 {event['hp_change']} HP"
    
    curse_text = f"\n🌀 Проклятие +{event['curse']}" if event["curse"] > 0 else ""
    
    return (
        f"🌍 <b>Исследование</b>\n\n"
        f"{event['text']}\n"
        f"🪙 +{event['coins']} монет{hp_text}{curse_text}\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}"
    )
    
def rest(player: dict) -> str:
    """Отдых у костра. Возвращает текст сообщения."""
    heal = random.randint(20, 40)
    player["hp"] = min(player["max_hp"], player["hp"] + heal)
    event = random.choice(REST_EVENTS)

    return (
        f"🏕 Ты разводишь костёр и отдыхаешь.\n"
        f"❤️ Восстановлено {heal} HP.\n"
        f"Текущее HP: {player['hp']}/{player['max_hp']}\n\n"
        f"<i>{event}</i>"
    )