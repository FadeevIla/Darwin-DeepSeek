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
    """Улучшенная команда получения яйца с вариативностью"""
    uid = str(message.from_user.id)
    arena = load_arena()
    player = arena["players"].get(uid)
    
    # Если у игрока уже есть питомец
    if player and player.get("pet_name"):
        out = []
        emojis = ["🥚", "🧬", "🪺", "✨"]
        for e in emojis:
            out.append(f"{e} У тебя уже есть питомец!")
            out.append(f"{e} Сначала избавься от старого!")
        out.append("")
        
        # Случайный юмор
        jokes = [
            "Яйца не бесконечны, знаешь ли!",
            "Твой карман трещит по швам от яиц!",
            "Хватит уже коллекционировать!",
            "Ты что, фермер-миллионер?"
        ]
        out.append(f"🤣 {random.choice(jokes)}")
        return await message.reply("\n".join(out))
    
    # Разные типы яиц
    eggs = [
        {"type": "обычное", "emoji": "🥚", "chance": 50, "color": "белое"},
        {"type": "золотое", "emoji": "🥚✨", "chance": 20, "color": "золотое"},
        {"type": "огненное", "emoji": "🥚🔥", "chance": 15, "color": "огненное"},
        {"type": "ледяное", "emoji": "🥚❄️", "chance": 10, "color": "ледяное"},
        {"type": "космическое", "emoji": "🥚🌌", "chance": 5, "color": "звёздное"}
    ]
    
    # Выбор яйца по весу
    weights = [e["chance"] for e in eggs]
    chosen = random.choices(eggs, weights=weights, k=1)[0]
    
    # Создание питомца с характеристиками в зависимости от яйца
    stats_mod = {
        "обычное": {"hp": 100, "strength": 10, "agility": 10, "magic": 10, "defense": 10, "speed": 10},
        "золотое": {"hp": 120, "strength": 15, "agility": 15, "magic": 15, "defense": 15, "speed": 15},
        "огненное": {"hp": 110, "strength": 20, "agility": 10, "magic": 18, "defense": 8, "speed": 14},
        "ледяное": {"hp": 130, "strength": 8, "agility": 12, "magic": 22, "defense": 20, "speed": 8},
        "космическое": {"hp": 100, "strength": 25, "agility": 20, "magic": 25, "defense": 15, "speed": 20}
    }
    
    base = stats_mod[chosen["type"]]
    
    player = {
        "pet_name": f"Питомец из {chosen['type']} яйца",
        "pet_emoji": chosen["emoji"],
        "hp": base["hp"],
        "max_hp": base["hp"],
        "strength": base["strength"],
        "agility": base["agility"],
        "magic": base["magic"],
        "defense": base["defense"],
        "speed": base["speed"],
        "hunger": 100,
        "mood": 100,
        "level": 1,
        "xp": 0,
        "wins": 0,
        "losses": 0,
        "egg_type": chosen["type"],
        "egg_color": chosen["color"],
        "hatched": False
    }
    
    arena["players"][uid] = player
    save_arena(arena)
    
    # Форматируем ответ
    rarity_msg = ""
    if chosen["chance"] <= 15:
        rarity_msg = "⭐ РЕДКОСТЬ! ⭐"
    if chosen["chance"] <= 5:
        rarity_msg = "💫 ЛЕГЕНДАРНО! 💫"
    
    # Случайные реакции
    reactions = [
        f"Ты получил {chosen['emoji']}!",
        f"Яйцо {chosen['color']} появилось из ниоткуда!",
        f"В воздухе запахло {chosen['type']} энергией!"
    ]
    
    out = []
    out.append("━━━━━━━━━━━━━━━━")
    out.append(f"🐣 <b>НОВОЕ ЯЙЦО!</b>")
    out.append("━━━━━━━━━━━━━━━━")
    out.append(f"{random.choice(reactions)}")
    out.append(f"")
    out.append(f"📦 Тип: {chosen['emoji']} <b>{chosen['type'].upper()}</b>")
    out.append(f"🎨 Цвет: <i>{chosen['color']}</i>")
    if rarity_msg:
        out.append(f"🏆 {rarity_msg}")
    out.append(f"")
    out.append("📊 <b>Базовые характеристики:</b>")
    out.append(f"❤️ HP: {base['hp']}")
    out.append(f"💪 Сила: {base['strength']}")
    out.append(f"🏃 Скорость: {base['speed']}")
    out.append(f"🛡️ Защита: {base['defense']}")
    out.append(f"🔮 Магия: {base['magic']}")
    out.append(f"💨 Ловкость: {base['agility']}")
    out.append(f"")
    out.append("💡 Используй /incubate чтобы высидеть яйцо!")
    out.append("━━━━━━━━━━━━━━━━")
    
    # Случайное дополнение
    if random.random() < 0.2:  # 20% шанс
        extras = [
            "🌟 Божественное благословение ускорит рост!",
            "🦋 Бабочка села на яйцо — к удаче!",
            "🌙 Лунный свет проникает сквозь скорлупу...",
            "⚡ Маленькая молния ударила в яйцо!"
        ]
        out.append(f"<i>{random.choice(extras)}</i>")
    
    return await message.reply("\n".join(out), parse_mode="HTML")
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
    """Улучшенная функция инкубации: 4 фазы, случайные события, визуальный прогресс."""
    uid = str(message.from_user.id)
    arena = load_arena()
    player = arena["players"].get(uid)

    if not player:
        await message.reply(
            "❌ У тебя ещё нет питомца!\n"
            "Сначала получи яйцо → /egg"
        )
        return

    if player.get("hatched", False):
        await message.reply(
            "🥚 <b>Твой питомец уже вылупился!</b>\n"
            "Он ждёт тебя в игре! Используй:\n"
            "🍽 /feed — покормить\n"
            "💪 /train — тренировать\n"
            "⚔️ /battle — сразиться"
        )
        return

    # Случайное событие при инкубации (шанс 30%)
    random_event = random.random()
    event_message = ""
    
    if random_event < 0.1:  # 10% — удача
        bonus_inc = 2
        event_message = (
            f"🌟 <b>Удача!</b> Яйцо поймало солнечный луч! 🌟\n"
            f"Прогресс увеличен на +{bonus_inc}!"
        )
    elif random_event < 0.2:  # 10% — неудача
        penalty_inc = -1
        event_message = (
            f"🌩️ <b>Ой!</b> Яйцо задрожало от грома... 🌩️\n"
            f"Прогресс уменьшен на {penalty_inc}!"
        )
    else:  # 80% — обычный инкубатор
        event_message = (
            f"🔥 Яйцо согревается в тепле инкубатора... 🔥"
        )

    # Применяем эффект события
    inc_progress = player.get("inc_progress", 0)
    if random_event < 0.1:
        inc_progress += 2
    elif random_event < 0.2:
        inc_progress -= 1
    else:
        inc_progress += 1

    # Гарантируем, что прогресс не уйдёт в минус
    if inc_progress < 0:
        inc_progress = 0

    # Определяем фазу инкубации
    phases = [
        (0, "🥚 Яйцо только что получено. Оно холодное и неподвижное."),
        (1, "🥚 Яйцо начинает слегка вибрировать. Внутри слышно слабое постукивание!"),
        (2, "⚡ Яйцо светится! Трещины медленно ползут по скорлупе."),
        (3, "🔥 Яйцо почти готово! Оно ходит ходуном! Осталось последнее усилие!")
    ]
    
    current_phase = 0
    current_desc = ""
    for phase_progress, desc in phases:
        if inc_progress >= phase_progress:
            current_phase = phase_progress
            current_desc = desc

    # Создаём визуальный прогресс-бар (макс 4 стадии)
    progress_bar = ""
    for i in range(4):
        if i < inc_progress:
            progress_bar += "🟢"
        else:
            progress_bar += "⚫"

    # Проверка на вылупление
    if inc_progress >= 4:
        # Генерация уникального питомца со случайными характеристиками
        pet_types = [
            {"name": "Огненный Дракон", "emoji": "🐉", "bonus_hp": 20, "bonus_str": 5},
            {"name": "Ледяной Феникс", "emoji": "🦅", "bonus_hp": 15, "bonus_magic": 7},
            {"name": "Каменный Голем", "emoji": "🗿", "bonus_hp": 30, "bonus_def": 8},
            {"name": "Теневой Волк", "emoji": "🐺", "bonus_hp": 18, "bonus_agi": 6},
        ]
        
        chosen_pet = random.choice(pet_types)
        
        player["hatched"] = True
        player["pet_name"] = chosen_pet["name"]
        player["pet_emoji"] = chosen_pet["emoji"]
        player["hp"] = 50 + chosen_pet["bonus_hp"]
        player["max_hp"] = 50 + chosen_pet["bonus_hp"]
        player["strength"] = 5 + chosen_pet.get("bonus_str", 0)
        player["agility"] = 5 + chosen_pet.get("bonus_agi", 0)
        player["magic"] = 5 + chosen_pet.get("bonus_magic", 0)
        player["defense"] = 5 + chosen_pet.get("bonus_def", 0)
        player["speed"] = 5 + random.randint(1, 5)
        player["hunger"] = 100
        player["mood"] = 100
        player["level"] = 1
        player["xp"] = 0
        player["wins"] = 0
        player["losses"] = 0
        player["inc_progress"] = 0
        
        await message.reply(
            f"🎉🎉🎉 <b>ЯЙЦО ВЫЛУПИЛОСЬ!</b> 🎉🎉🎉\n\n"
            f"{chosen_pet['emoji']} <b>Поздравляю!</b>\n"
            f"У тебя родился <b>{chosen_pet['name']}</b>!\n\n"
            f"📊 <b>Базовые характеристики:</b>\n"
            f"❤️ HP: {player['max_hp']}\n"
            f"⚔️ Сила: {player['strength']}\n"
            f"🦅 Ловкость: {player['agility']}\n"
            f"🔮 Магия: {player['magic']}\n"
            f"🛡️ Защита: {player['defense']}\n"
            f"💨 Скорость: {player['speed']}\n\n"
            f"🐾 Начни ухаживать за питомцем:\n"
            f"🍽 /feed — покормить\n"
            f"💪 /train — тренировать\n"
            f"⚔️ /battle — сразиться\n"
            f"📋 /stats — статистика"
        )
    else:
        player["inc_progress"] = inc_progress
        
        # Прогноз следующей фазы
        if current_phase < 3:
            next_phase_descs = [
                "Скоро начнёт вибрировать...",
                "Скоро появится свечение...",
                "Осталось чуть-чуть до вылупления!"
            ]
            next_desc = next_phase_descs[current_phase]
        else:
            next_desc = "Яйцо готово! Ещё раз и оно вылупится!"

        await message.reply(
            f"🥚 <b>Инкубация яйца</b> 🥚\n\n"
            f"{event_message}\n\n"
            f"📈 <b>Прогресс:</b> {inc_progress}/4\n"
            f"{progress_bar}\n\n"
            f"🔬 <b>Текущая фаза:</b>\n{current_desc}\n\n"
            f"🔮 <b>Прогноз:</b> {next_desc}\n\n"
            f"💡 <i>Повторяй /incubate, чтобы ускорить вылупление!</i>\n"
            f"🌤️ <i>Будь внимателен — погода влияет на инкубацию!</i>"
        )

    save_arena(arena)
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
    """Битва с другим игроком или ботом"""
    uid = str(message.from_user.id)
    arena = load_arena()
    player = arena["players"].get(uid)
    
    if not player:
        await message.reply("❌ У тебя нет питомца! Используй /egg")
        return
    
    # Проверка на яйцо
    if player.get("egg"):
        await message.reply("🥚 Твой питомец ещё в яйце! Используй /incubate")
        return
    
    # Проверка здоровья
    if player["hp"] <= 0:
        await message.reply("💀 Твой питомец без сознания! Используй /feed для восстановления")
        return
    
    # Определяем противника
    args = message.get_args()
    opponent_uid = None
    is_bot = False
    
    if args:
        # Попытка найти игрока по нику или id
        for pid, pdata in arena["players"].items():
            if pdata.get("username") == args or pid == args:
                opponent_uid = pid
                break
        
        if not opponent_uid:
            await message.reply("❌ Игрок не найден! Используй /battle для битвы с ботом")
            return
    else:
        # Битва с ботом
        is_bot = True
    
    # Создаём противника
    if is_bot:
        # Определяем уровень бота на основе уровня игрока
        player_level = player.get("level", 1)
        
        # Разные типы ботов с разной сложностью
        bot_templates = [
            {"name": "Дикий волк", "emoji": "🐺", "hp": 80, "max_hp": 80, "strength": 12, "agility": 10, "magic": 5, "defense": 8, "speed": 14, "level": 1},
            {"name": "Лесной тролль", "emoji": "🧌", "hp": 120, "max_hp": 120, "strength": 15, "agility": 5, "magic": 3, "defense": 12, "speed": 6, "level": 2},
            {"name": "Теневой маг", "emoji": "🧙", "hp": 70, "max_hp": 70, "strength": 8, "agility": 12, "magic": 18, "defense": 6, "speed": 10, "level": 3},
            {"name": "Каменный голем", "emoji": "🗿", "hp": 150, "max_hp": 150, "strength": 18, "agility": 3, "magic": 2, "defense": 20, "speed": 4, "level": 4},
            {"name": "Дракон-подросток", "emoji": "🐉", "hp": 100, "max_hp": 100, "strength": 14, "agility": 8, "magic": 10, "defense": 10, "speed": 8, "level": 5},
        ]
        
        # Выбираем бота в зависимости от уровня игрока
        if player_level <= 2:
            bot_template = bot_templates[0]
        elif player_level <= 4:
            bot_template = random.choice(bot_templates[:3])
        elif player_level <= 6:
            bot_template = random.choice(bot_templates[2:4])
        else:
            bot_template = random.choice(bot_templates[3:])
        
        # Масштабируем бота под уровень игрока
        scale = 1 + (player_level - bot_template["level"]) * 0.1
        opponent = {
            "pet_name": bot_template["name"],
            "pet_emoji": bot_template["emoji"],
            "hp": int(bot_template["hp"] * scale),
            "max_hp": int(bot_template["max_hp"] * scale),
            "strength": int(bot_template["strength"] * scale),
            "agility": int(bot_template["agility"] * scale),
            "magic": int(bot_template["magic"] * scale),
            "defense": int(bot_template["defense"] * scale),
            "speed": int(bot_template["speed"] * scale),
            "level": player_level,
        }
    else:
        opponent = arena["players"].get(opponent_uid)
        if not opponent:
            await message.reply("❌ Игрок не найден!")
            return
        
        if opponent.get("egg"):
            await message.reply("🥚 Противник ещё в яйце! Подожди")
            return
        
        if opponent["hp"] <= 0:
            await message.reply("💀 Противник без сознания!")
            return
    
    # Симуляция боя
    player_hp = player["hp"]
    opponent_hp = opponent["hp"]
    
    battle_log = []
    turn = 1
    max_turns = 20
    
    # Определяем, кто ходит первым (по скорости)
    player_speed = player.get("speed", 10)
    opponent_speed = opponent.get("speed", 10)
    
    player_first = player_speed >= opponent_speed
    
    while player_hp > 0 and opponent_hp > 0 and turn <= max_turns:
        if (player_first and turn % 2 == 1) or (not player_first and turn % 2 == 0):
            # Ход игрока
            # Выбор атаки
            attack_type = random.choices(
                ["strength", "agility", "magic"],
                weights=[player.get("strength", 10), player.get("agility", 10), player.get("magic", 10)]
            )[0]
            
            base_damage = player.get(attack_type, 10)
            # Критический удар (20% шанс)
            if random.random() < 0.2:
                base_damage = int(base_damage * 2.5)
                crit_text = " 💥 КРИТИЧЕСКИЙ УДАР!"
            else:
                crit_text = ""
            
            # Защита противника
            defense = opponent.get("defense", 5)
            damage = max(1, base_damage - defense // 2)
            
            # Случайный разброс
            damage = max(1, int(damage * random.uniform(0.8, 1.2)))
            
            opponent_hp -= damage
            battle_log.append(f"⚔️ Ты атакуешь {attack_type} и наносишь {damage} урона!{crit_text}")
            
            # Проклятие (10% шанс на штраф)
            if random.random() < 0.1:
                curse_type = random.choice(["strength", "agility", "magic", "defense", "speed"])
                curse_amount = random.randint(1, 3)
                player[curse_type] = max(1, player.get(curse_type, 10) - curse_amount)
                battle_log.append(f"😈 Проклятие! {curse_type} уменьшено на {curse_amount}!")
        else:
            # Ход противника
            # Выбор атаки противника
            attack_type = random.choices(
                ["strength", "agility", "magic"],
                weights=[opponent.get("strength", 10), opponent.get("agility", 10), opponent.get("magic", 10)]
            )[0]
            
            base_damage = opponent.get(attack_type, 10)
            # Критический удар врага (15% шанс)
            if random.random() < 0.15:
                base_damage = int(base_damage * 2.0)
                crit_text = " 💥 КРИТИЧЕСКИЙ УДАР!"
            else:
                crit_text = ""
            
            # Защита игрока
            defense = player.get("defense", 5)
            damage = max(1, base_damage - defense // 2)
            
            # Случайный разброс
            damage = max(1, int(damage * random.uniform(0.8, 1.2)))
            
            player_hp -= damage
            battle_log.append(f"💢 {opponent['pet_emoji']} {opponent['pet_name']} атакует {attack_type} и наносит {damage} урона!{crit_text}")
            
            # Проклятие для игрока (8% шанс)
            if random.random() < 0.08:
                curse_type = random.choice(["strength", "agility", "magic", "defense", "speed"])
                curse_amount = random.randint(1, 2)
                player[curse_type] = max(1, player.get(curse_type, 10) - curse_amount)
                battle_log.append(f"😈 Проклятие! Твой {curse_type} уменьшен на {curse_amount}!")
        
        turn += 1
    
    # Определение победителя
    if player_hp <= 0:
        winner = "opponent"
        player["losses"] = player.get("losses", 0) + 1
        if not is_bot:
            opponent["wins"] = opponent.get("wins", 0) + 1
    elif opponent_hp <= 0:
        winner = "player"
        player["wins"] = player.get("wins", 0) + 1
        # Награда за победу
        xp_gain = random.randint(10, 30) * (1 + opponent.get("level", 1) // 2)
        player["xp"] = player.get("xp", 0) + xp_gain
        # Проверка на повышение уровня
        if player["xp"] >= player.get("level", 1) * 100:
            player["level"] = player.get("level", 1) + 1
            player["xp"] = 0
            player["max_hp"] = player.get("max_hp", 100) + 10
            player["hp"] = player["max_hp"]
            battle_log.append(f"🎉 УРОВЕНЬ ПОВЫШЕН! Теперь ты {player['level']} уровня!")
        
        if not is_bot:
            opponent["losses"] = opponent.get("losses", 0) + 1
    else:
        # Ничья
        winner = "draw"
        player["losses"] = player.get("losses", 0) + 1
        if not is_bot:
            opponent["losses"] = opponent.get("losses", 0) + 1
    
    # Обновление здоровья
    player["hp"] = max(0, player_hp)
    if not is_bot:
        opponent["hp"] = max(0, opponent_hp)
    
    # Голод увеличивается после боя
    player["hunger"] = min(100, player.get("hunger", 0) + 15)
    
    # Сохранение
    arena["players"][uid] = player
    if not is_bot and opponent_uid:
        arena["players"][opponent_uid] = opponent
    save_arena(arena)
    
    # Формирование отчёта
    result_text = ""
    if winner == "player":
        result_text = f"🎉 ПОБЕДА! Ты одолел {opponent['pet_emoji']} {opponent['pet_name']}!"
    elif winner == "opponent":
        result_text = f"💀 ПОРАЖЕНИЕ! {opponent['pet_emoji']} {opponent['pet_name']} одолел тебя!"
    else:
        result_text = "🤝 НИЧЬЯ! Оба питомца выдохлись!"
    
    report = f"⚔️ **БИТВА** ⚔️\n\n"
    report += f"{player['pet_emoji']} **{player['pet_name']}** (Ур.{player.get('level', 1)}) VS "
    report += f"{opponent['pet_emoji']} **{opponent['pet_name']}** (Ур.{opponent.get('level', 1)})\n\n"
    report += f"**Итог:** {result_text}\n\n"
    report += "**Ход битвы:**\n"
    report += "\n".join(battle_log[-10:])  # Показываем последние 10 ходов
    report += f"\n\n**Твой питомец:** ❤️ {player['hp']}/{player['max_hp']} | 🍖 {player.get('hunger', 0)}%"
    
    await message.reply(report)
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