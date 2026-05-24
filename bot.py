# bot.py — Тамагочи-Арена "Уроборос"
"""Вырасти питомца и сразись на арене!"""
import os
import sys
import json
import random
import logging
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

from core.health_server import start_health_server
from core.feedback import add_feedback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ARENA_FILE = "arena.json"


# ============================================================
# БАЗА ДАННЫХ
# ============================================================

def load_arena():
    if not os.path.exists(ARENA_FILE):
        return {"players": {}}
    with open(ARENA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_arena(data):
    with open(ARENA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# ПИТОМЦЫ
# ============================================================

PETS = [
    {"name": "Огненный змей", "emoji": "🐍", "bonus": "strength"},
    {"name": "Ледяной волк", "emoji": "🐺", "bonus": "agility"},
    {"name": "Теневой ворон", "emoji": "🦅", "bonus": "magic"},
    {"name": "Каменный голем", "emoji": "🗿", "bonus": "defense"},
    {"name": "Призрачный кот", "emoji": "🐱", "bonus": "speed"},
]


def random_pet():
    pet = random.choice(PETS).copy()
    pet["hp"] = 100
    pet["max_hp"] = 100
    pet["strength"] = random.randint(5, 15)
    pet["agility"] = random.randint(5, 15)
    pet["magic"] = random.randint(5, 15)
    pet["defense"] = random.randint(5, 15)
    pet["speed"] = random.randint(5, 15)
    pet["hunger"] = 100
    pet["mood"] = 100
    pet["level"] = 1
    pet["xp"] = 0
    pet["wins"] = 0
    pet["losses"] = 0
    pet["created"] = datetime.now(timezone.utc).isoformat()
    return pet


# ============================================================
# КОМАНДЫ
# ============================================================

async def start_cmd(message: types.Message):
    arena = load_arena()
    uid = str(message.from_user.id)

    if uid in arena["players"] and arena["players"][uid].get("pet"):
        pet = arena["players"][uid]["pet"]
        await message.reply(
            f"🐉 <b>УРОБОРОС: АРЕНА</b>\n\n"
            f"Твой питомец: {pet.get('emoji', '❓')} <b>{pet.get('name', 'Неизвестный')}</b>\n"
            f"❤️ HP: {pet.get('hp', 0)}/{pet.get('max_hp', 100)}\n"
            f"⭐ Уровень: {pet.get('level', 1)}\n"
            f"🍗 Голод: {pet.get('hunger', 0)}/100\n"
            f"😊 Настроение: {pet.get('mood', 0)}/100\n\n"
            f"/feed — Покормить\n"
            f"/train — Тренировать\n"
            f"/battle — На арену!\n"
            f"/top — Таблица лидеров\n"
            f"/help — Все команды",
            parse_mode="HTML"
        )
    else:
        await message.reply(
            "🐉 <b>УРОБОРОС: АРЕНА</b>\n\n"
            "Добро пожаловать! Здесь ты вырастишь питомца и сразишься с другими игроками.\n\n"
            "Напиши /egg чтобы получить яйцо!",
            parse_mode="HTML"
        )


async def egg_cmd(message: types.Message):
    arena = load_arena()
    uid = str(message.from_user.id)

    if uid not in arena["players"]:
        arena["players"][uid] = {}

    if arena["players"][uid].get("pet"):
        await message.reply("У тебя уже есть питомец! Используй /start.")
        return

    arena["players"][uid]["egg"] = {
        "created": datetime.now(timezone.utc).isoformat(),
        "incubated": False,
    }
    save_arena(arena)

    await message.reply(
        "🥚 <b>Яйцо получено!</b>\n\n"
        "Теперь его нужно высиживать!\n"
        "Напиши /incubate чтобы согреть яйцо.\n"
        "Нужно сделать это 3 раза, чтобы вылупился питомец.",
        parse_mode="HTML"
    )


async def incubate_cmd(message: types.Message):
    arena = load_arena()
    uid = str(message.from_user.id)

    if uid not in arena["players"] or "egg" not in arena["players"][uid]:
        await message.reply("У тебя нет яйца! Напиши /egg.")
        return

    egg = arena["players"][uid]["egg"]
    egg["incubated"] = egg.get("incubated", False)

    if egg["incubated"]:
        await message.reply("Яйцо уже согрето! Подожди немного...")
        return

    egg["warmth"] = egg.get("warmth", 0) + 1

    if egg["warmth"] >= 3:
        pet = random_pet()
        arena["players"][uid]["pet"] = pet
        del arena["players"][uid]["egg"]
        save_arena(arena)

        await message.reply(
            f"🎉 <b>Яйцо треснуло!</b>\n\n"
            f"Из него вылупился: {pet['emoji']} <b>{pet['name']}</b>!\n"
            f"⚡ Сила: {pet['strength']}\n"
            f"💨 Ловкость: {pet['agility']}\n"
            f"🔮 Магия: {pet['magic']}\n"
            f"🛡️ Защита: {pet['defense']}\n"
            f"💫 Скорость: {pet['speed']}\n\n"
            f"Теперь расти его! /feed и /train",
            parse_mode="HTML"
        )
    else:
        save_arena(arena)
        await message.reply(
            f"🔥 Яйцо согрето! ({egg['warmth']}/3)\n"
            f"Напиши /incubate ещё раз через минуту.",
            parse_mode="HTML"
        )


async def feed_cmd(message: types.Message):
    arena = load_arena()
    uid = str(message.from_user.id)

    if uid not in arena["players"] or "pet" not in arena["players"][uid]:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return

    pet = arena["players"][uid]["pet"]
    pet["hunger"] = min(100, pet["hunger"] + random.randint(20, 40))
    pet["mood"] = min(100, pet["mood"] + random.randint(5, 15))
    pet["hp"] = min(pet["max_hp"], pet["hp"] + random.randint(5, 15))

    save_arena(arena)

    food = random.choice(["🍗 курицу", "🍎 яблоко", "🐟 рыбу", "🍖 мясо", "🧪 зелье"])
    await message.reply(
        f"🍽 Ты покормил питомца: {food}!\n"
        f"🍗 Голод: {pet['hunger']}/100\n"
        f"😊 Настроение: {pet['mood']}/100\n"
        f"❤️ HP: {pet['hp']}/{pet['max_hp']}",
        parse_mode="HTML"
    )


async def train_cmd(message: types.Message):
    arena = load_arena()
    uid = str(message.from_user.id)

    if uid not in arena["players"] or "pet" not in arena["players"][uid]:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return

    pet = arena["players"][uid]["pet"]

    trainings = ["strength", "agility", "magic", "defense", "speed"]
    stat = random.choice(trainings)
    boost = random.randint(1, 3)
    pet[stat] += boost
    pet["xp"] += random.randint(10, 30)
    pet["hunger"] = max(0, pet["hunger"] - random.randint(10, 25))
    pet["mood"] = max(0, pet["mood"] - random.randint(5, 10))

    # Уровень
    if pet["xp"] >= pet["level"] * 50:
        pet["level"] += 1
        pet["xp"] = 0
        pet["max_hp"] += 15
        pet["hp"] = pet["max_hp"]
        pet["strength"] += 2
        pet["agility"] += 2
        pet["magic"] += 2
        pet["defense"] += 2
        pet["speed"] += 2
        level_up = " 🎉 УРОВЕНЬ ПОВЫШЕН!"
    else:
        level_up = ""

    save_arena(arena)

    stat_names = {"strength": "⚡ Сила", "agility": "💨 Ловкость", "magic": "🔮 Магия", "defense": "🛡️ Защита",
                  "speed": "💫 Скорость"}
    await message.reply(
        f"🏋️ Тренировка завершена!\n"
        f"{stat_names[stat]}: +{boost}\n"
        f"✨ Опыт: {pet['xp']}/{pet['level'] * 50}\n"
        f"🍗 Голод: {pet['hunger']}/100\n"
        f"😊 Настроение: {pet['mood']}/100{level_up}",
        parse_mode="HTML"
    )


async def battle_cmd(message: types.Message):
    arena = load_arena()
    uid = str(message.from_user.id)

    if uid not in arena["players"] or "pet" not in arena["players"][uid]:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return

    # Ищем соперника
    opponents = [p for p in arena["players"] if p != uid and "pet" in arena["players"][p]]

    if not opponents:
        # Бой с ботом
        bot_pet = random_pet()
        bot_pet["name"] = "Дикий " + bot_pet["name"]
        my_pet = arena["players"][uid]["pet"]

        my_power = my_pet["strength"] + my_pet["agility"] + my_pet["level"] * 5
        bot_power = bot_pet["strength"] + bot_pet["agility"] + bot_pet["level"] * 3

        if my_power >= bot_power:
            my_pet["wins"] += 1
            my_pet["xp"] += 30
            result = f"⚔️ Победа над {bot_pet['emoji']} {bot_pet['name']}!\n+30 XP"
        else:
            my_pet["losses"] += 1
            my_pet["hp"] = max(1, my_pet["hp"] - 20)
            result = f"💔 Поражение от {bot_pet['emoji']} {bot_pet['name']}...\n-20 HP"

        save_arena(arena)
        await message.reply(result, parse_mode="HTML")
    else:
        opp_id = random.choice(opponents)
        opp_pet = arena["players"][opp_id]["pet"]
        my_pet = arena["players"][uid]["pet"]

        my_power = my_pet["strength"] + my_pet["agility"] + my_pet["level"] * 5
        opp_power = opp_pet["strength"] + opp_pet["agility"] + opp_pet["level"] * 5

        if my_power >= opp_power:
            my_pet["wins"] += 1
            opp_pet["losses"] += 1
            my_pet["xp"] += 50
            result = f"⚔️ Победа над {opp_pet['emoji']} {opp_pet['name']}!\n+50 XP"
        else:
            my_pet["losses"] += 1
            opp_pet["wins"] += 1
            my_pet["hp"] = max(1, my_pet["hp"] - 25)
            result = f"💔 Поражение от {opp_pet['emoji']} {opp_pet['name']}...\n-25 HP"

        save_arena(arena)
        await message.reply(result, parse_mode="HTML")


async def top_cmd(message: types.Message):
    arena = load_arena()

    # Сортируем по победам
    ranked = []
    for uid, data in arena["players"].items():
        if "pet" in data:
            pet = data["pet"]
            ranked.append((uid, pet["name"], pet["emoji"], pet["wins"], pet["losses"], pet["level"]))

    ranked.sort(key=lambda x: x[3], reverse=True)

    if not ranked:
        await message.reply("Пока никто не участвовал в битвах!")
        return

    lines = ["🏆 <b>ТАБЛИЦА ЛИДЕРОВ</b>\n"]
    for i, (uid, name, emoji, wins, losses, level) in enumerate(ranked[:10], 1):
        lines.append(f"{i}. {emoji} {name} — {wins}W/{losses}L, lvl {level}")

    await message.reply("\n".join(lines), parse_mode="HTML")


async def help_cmd(message: types.Message):
    await message.reply(
        "🐉 <b>УРОБОРОС: АРЕНА</b>\n\n"
        "🥚 /egg — Получить яйцо\n"
        "🔥 /incubate — Согреть яйцо (нужно 3 раза)\n"
        "🍽 /feed — Покормить питомца\n"
        "🏋️ /train — Тренировать\n"
        "⚔️ /battle — Сразиться на арене\n"
        "🏆 /top — Таблица лидеров\n"
        "📊 /stats — Статистика питомца\n"
        "📝 /report — Сообщить о баге",
        parse_mode="HTML"
    )


async def stats_cmd(message: types.Message):
    arena = load_arena()
    uid = str(message.from_user.id)

    if uid not in arena["players"] or "pet" not in arena["players"][uid]:
        await message.reply("У тебя нет питомца!")
        return

    pet = arena["players"][uid]["pet"]
    await message.reply(
        f"📊 <b>{pet['emoji']} {pet['name']}</b>\n"
        f"⭐ Уровень: {pet['level']} ({pet['xp']}/{pet['level'] * 50} XP)\n"
        f"❤️ HP: {pet['hp']}/{pet['max_hp']}\n"
        f"⚡ Сила: {pet['strength']}\n"
        f"💨 Ловкость: {pet['agility']}\n"
        f"🔮 Магия: {pet['magic']}\n"
        f"🛡️ Защита: {pet['defense']}\n"
        f"💫 Скорость: {pet['speed']}\n"
        f"🍗 Голод: {pet['hunger']}/100\n"
        f"😊 Настроение: {pet['mood']}/100\n"
        f"🏆 Победы: {pet['wins']} | 💀 Поражения: {pet['losses']}",
        parse_mode="HTML"
    )


async def report_cmd(message: types.Message):
    if message.from_user.id != 6909561387:
        await message.reply("⛔ Только для администратора.")
        return
    text = message.get_args()
    if not text:
        await message.reply("📝 /report текст")
        return
    add_feedback(text, "admin")
    await message.reply("✅ Отправлено!")


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не установлен!")
        sys.exit(1)

    start_health_server()

    # Создаём arena.json если нет
    if not os.path.exists(ARENA_FILE):
        save_arena({"players": {}})

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    dp.register_message_handler(start_cmd, commands=['start'])
    dp.register_message_handler(egg_cmd, commands=['egg'])
    dp.register_message_handler(incubate_cmd, commands=['incubate'])
    dp.register_message_handler(feed_cmd, commands=['feed'])
    dp.register_message_handler(train_cmd, commands=['train'])
    dp.register_message_handler(battle_cmd, commands=['battle'])
    dp.register_message_handler(top_cmd, commands=['top'])
    dp.register_message_handler(help_cmd, commands=['help'])
    dp.register_message_handler(stats_cmd, commands=['stats'])
    dp.register_message_handler(report_cmd, commands=['report'])

    logger.info("🐉 Уроборос: Арена запущена!")
    executor.start_polling(dp)