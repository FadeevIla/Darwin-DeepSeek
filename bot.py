# bot.py — Тамагочи-Арена "Уроборос"
"""Вырасти питомца и сразись на арене!"""
import os
import sys
import json
import random
import logging
from pathlib import Path
from datetime import datetime, timezone
from supabase import create_client, Client

# Supabase конфигурация
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

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
# БАЗА ДАННЫХ (Supabase)
# ============================================================

def get_player(uid: str) -> dict:
    """Получает данные игрока из Supabase."""
    if not supabase:
        return None
    try:
        response = supabase.table("players").select("*").eq("user_id", int(uid)).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Ошибка загрузки игрока: {e}")
        return None

def create_player(uid: str) -> dict:
    """Создаёт нового игрока в Supabase."""
    if not supabase:
        return None
    pet = random_pet()
    player_data = {
        "user_id": int(uid),
        "pet_name": pet["name"],
        "pet_emoji": pet["emoji"],
        "hp": pet["hp"],
        "max_hp": pet["max_hp"],
        "strength": pet["strength"],
        "agility": pet["agility"],
        "magic": pet["magic"],
        "defense": pet["defense"],
        "speed": pet["speed"],
        "hunger": pet["hunger"],
        "mood": pet["mood"],
        "level": pet["level"],
        "xp": pet["xp"],
        "wins": pet["wins"],
        "losses": pet["losses"],
    }
    try:
        supabase.table("players").insert(player_data).execute()
        return player_data
    except Exception as e:
        logger.error(f"Ошибка создания игрока: {e}")
        return None

def update_player(uid: str, data: dict):
    """Обновляет данные игрока в Supabase."""
    if not supabase:
        return
    try:
        supabase.table("players").update(data).eq("user_id", int(uid)).execute()
    except Exception as e:
        logger.error(f"Ошибка обновления игрока: {e}")

def get_top_players(limit: int = 10) -> list:
    """Возвращает топ игроков по победам."""
    if not supabase:
        return []
    try:
        response = supabase.table("players").select("*").order("wins", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Ошибка загрузки топа: {e}")
        return []

def get_random_opponent(uid: str) -> dict:
    """Находит случайного соперника для битвы."""
    if not supabase:
        return None
    try:
        response = supabase.table("players").select("*").neq("user_id", int(uid)).execute()
        if response.data:
            import random
            return random.choice(response.data)
        return None
    except Exception as e:
        logger.error(f"Ошибка поиска соперника: {e}")
        return None


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
    uid = str(message.from_user.id)
    player = get_player(uid)

    if player:
        await message.reply(
            f"🐉 <b>УРОБОРОС: АРЕНА</b>\n\n"
            f"Твой питомец: {player.get('pet_emoji', '❓')} <b>{player.get('pet_name', 'Неизвестный')}</b>\n"
            f"❤️ HP: {player.get('hp', 0)}/{player.get('max_hp', 100)}\n"
            f"⭐ Уровень: {player.get('level', 1)}\n"
            f"🍗 Голод: {player.get('hunger', 0)}/100\n"
            f"😊 Настроение: {player.get('mood', 0)}/100\n\n"
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
    uid = str(message.from_user.id)
    player = get_player(uid)

    if player:
        await message.reply("У тебя уже есть питомец! Используй /start.")
        return

    player = create_player(uid)
    if player:
        await message.reply(
            "🥚 <b>Яйцо получено!</b>\n\n"
            f"Из него вылупился: {player['pet_emoji']} <b>{player['pet_name']}</b>!\n\n"
            f"Теперь расти его! /feed и /train",
            parse_mode="HTML"
        )
    else:
        await message.reply("❌ Ошибка при создании питомца. Попробуй позже.")


async def stats_cmd(message: types.Message):
    uid = str(message.from_user.id)
    player = get_player(uid)

    if not player:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return

    await message.reply(
        f"📊 <b>{player['pet_emoji']} {player['pet_name']}</b>\n"
        f"⭐ Уровень: {player['level']} ({player['xp']}/{player['level'] * 50} XP)\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
        f"⚡ Сила: {player['strength']}\n"
        f"💨 Ловкость: {player['agility']}\n"
        f"🔮 Магия: {player['magic']}\n"
        f"🛡️ Защита: {player['defense']}\n"
        f"💫 Скорость: {player['speed']}\n"
        f"🍗 Голод: {player['hunger']}/100\n"
        f"😊 Настроение: {player['mood']}/100\n"
        f"🏆 Победы: {player['wins']} | 💀 Поражения: {player['losses']}",
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
    uid = str(message.from_user.id)
    player = get_player(uid)

    if not player:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return

    new_hunger = min(100, player["hunger"] + random.randint(20, 40))
    new_mood = min(100, player["mood"] + random.randint(5, 15))
    new_hp = min(player["max_hp"], player["hp"] + random.randint(5, 15))

    update_player(uid, {"hunger": new_hunger, "mood": new_mood, "hp": new_hp})

    food = random.choice(["🍗 курицу", "🍎 яблоко", "🐟 рыбу", "🍖 мясо", "🧪 зелье"])
    await message.reply(
        f"🍽 Ты покормил питомца: {food}!\n"
        f"🍗 Голод: {new_hunger}/100\n"
        f"😊 Настроение: {new_mood}/100\n"
        f"❤️ HP: {new_hp}/{player['max_hp']}",
        parse_mode="HTML"
    )


async def train_cmd(message: types.Message):
    uid = str(message.from_user.id)
    player = get_player(uid)

    if not player:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return

    trainings = ["strength", "agility", "magic", "defense", "speed"]
    stat = random.choice(trainings)
    boost = random.randint(1, 3)

    new_data = {
        stat: player[stat] + boost,
        "xp": player["xp"] + random.randint(10, 30),
        "hunger": max(0, player["hunger"] - random.randint(10, 25)),
        "mood": max(0, player["mood"] - random.randint(5, 10)),
    }

    # Уровень
    if new_data["xp"] >= player["level"] * 50:
        new_data["level"] = player["level"] + 1
        new_data["xp"] = 0
        new_data["max_hp"] = player["max_hp"] + 15
        new_data["hp"] = new_data["max_hp"]
        new_data["strength"] = player["strength"] + boost + 2
        new_data["agility"] = player["agility"] + boost + 2
        new_data["magic"] = player["magic"] + boost + 2
        new_data["defense"] = player["defense"] + boost + 2
        new_data["speed"] = player["speed"] + boost + 2
        level_up = " 🎉 УРОВЕНЬ ПОВЫШЕН!"
    else:
        level_up = ""

    update_player(uid, new_data)

    stat_names = {"strength": "⚡ Сила", "agility": "💨 Ловкость", "magic": "🔮 Магия", "defense": "🛡️ Защита",
                  "speed": "💫 Скорость"}
    await message.reply(
        f"🏋️ Тренировка завершена!\n"
        f"{stat_names[stat]}: +{boost}\n"
        f"✨ Опыт: {new_data['xp']}/{player['level'] * 50}\n"
        f"🍗 Голод: {new_data['hunger']}/100\n"
        f"😊 Настроение: {new_data['mood']}/100{level_up}",
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
    players = get_top_players(10)

    if not players:
        await message.reply("Пока никто не участвовал в битвах!")
        return

    lines = ["🏆 <b>ТАБЛИЦА ЛИДЕРОВ</b>\n"]
    for i, p in enumerate(players, 1):
        lines.append(f"{i}. {p.get('pet_emoji', '❓')} {p['pet_name']} — {p['wins']}W/{p['losses']}L, lvl {p['level']}")

    await message.reply("\n".join(lines), parse_mode="HTML")


async def battle_cmd(message: types.Message):
    uid = str(message.from_user.id)
    player = get_player(uid)

    if not player:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return

    # Ищем реального соперника в Supabase
    opponent = get_random_opponent(uid)

    if opponent:
        # PvP битва с реальным игроком
        my_power = player["strength"] + player["agility"] + player["level"] * 5
        opp_power = opponent["strength"] + opponent["agility"] + opponent["level"] * 5

        if my_power >= opp_power:
            update_player(uid, {"wins": player["wins"] + 1, "xp": player["xp"] + 50})
            update_player(str(opponent["user_id"]), {"losses": opponent["losses"] + 1})
            result = f"⚔️ Победа над {opponent['pet_emoji']} {opponent['pet_name']}!\n+50 XP"
        else:
            update_player(uid, {"losses": player["losses"] + 1, "hp": max(1, player["hp"] - 25)})
            update_player(str(opponent["user_id"]), {"wins": opponent["wins"] + 1})
            result = f"💔 Поражение от {opponent['pet_emoji']} {opponent['pet_name']}...\n-25 HP"
    else:
        # Бой с ботом (если нет других игроков)
        bot_pet = random_pet()
        my_power = player["strength"] + player["agility"] + player["level"] * 5
        bot_power = bot_pet["strength"] + bot_pet["agility"] + bot_pet["level"] * 3

        if my_power >= bot_power:
            update_player(uid, {"wins": player["wins"] + 1, "xp": player["xp"] + 30})
            result = f"⚔️ Победа над {bot_pet['emoji']} диким {bot_pet['name']}!\n+30 XP"
        else:
            update_player(uid, {"losses": player["losses"] + 1, "hp": max(1, player["hp"] - 20)})
            result = f"💔 Поражение от {bot_pet['emoji']} дикого {bot_pet['name']}...\n-20 HP"

    await message.reply(result, parse_mode="HTML")


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