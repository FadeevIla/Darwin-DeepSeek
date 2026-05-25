# bot.py — Тамагочи-Арена "Уроборос" (Supabase)
"""Вырасти питомца и сразись на арене!"""
import os
import sys
import random
import logging
from pathlib import Path
from datetime import datetime, timezone

from supabase import create_client, Client

sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

from core.health_server import start_health_server
from core.feedback import add_feedback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Supabase конфигурация
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# ============================================================
# БАЗА ДАННЫХ (Supabase)
# ============================================================

def get_player(uid: str) -> dict | None:
    if not supabase:
        return None
    try:
        response = supabase.table("players").select("*").eq("user_id", int(uid)).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Ошибка загрузки игрока: {e}")
        return None

def create_player(uid: str) -> dict | None:
    if not supabase:
        return None
    pet = random_pet()
    player_data = {
        "user_id": int(uid),
        "pet_name": pet["name"],
        "pet_emoji": pet["emoji"],
        "hp": pet["hp"], "max_hp": pet["max_hp"],
        "strength": pet["strength"], "agility": pet["agility"],
        "magic": pet["magic"], "defense": pet["defense"],
        "speed": pet["speed"], "hunger": pet["hunger"],
        "mood": pet["mood"], "level": pet["level"],
        "xp": pet["xp"], "wins": pet["wins"], "losses": pet["losses"],
        "egg_type": "обычное", "hatched": False, "inc_progress": 0,
    }
    try:
        supabase.table("players").insert(player_data).execute()
        return player_data
    except Exception as e:
        logger.error(f"Ошибка создания игрока: {e}")
        return None

def update_player(uid: str, data: dict):
    if not supabase:
        return
    try:
        supabase.table("players").update(data).eq("user_id", int(uid)).execute()
    except Exception as e:
        logger.error(f"Ошибка обновления игрока: {e}")

def get_top_players(limit: int = 10) -> list:
    if not supabase:
        return []
    try:
        response = supabase.table("players").select("*").order("wins", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Ошибка загрузки топа: {e}")
        return []

def get_random_opponent(uid: str) -> dict | None:
    if not supabase:
        return None
    try:
        response = supabase.table("players").select("*").neq("user_id", int(uid)).execute()
        return random.choice(response.data) if response.data else None
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

def random_pet() -> dict:
    pet = random.choice(PETS).copy()
    pet.update({
        "hp": 100, "max_hp": 100,
        "strength": random.randint(5, 15), "agility": random.randint(5, 15),
        "magic": random.randint(5, 15), "defense": random.randint(5, 15),
        "speed": random.randint(5, 15), "hunger": 100, "mood": 100,
        "level": 1, "xp": 0, "wins": 0, "losses": 0,
        "created": datetime.now(timezone.utc).isoformat(),
    })
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
            f"/feed — Покормить\n/train — Тренировать\n/battle — На арену!\n"
            f"/top — Таблица лидеров\n/help — Все команды",
            parse_mode="HTML"
        )
    else:
        await message.reply(
            "🐉 <b>УРОБОРОС: АРЕНА</b>\n\n"
            "Добро пожаловать! Вырасти питомца и сразись с другими игроками.\n\n"
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
            f"🥚 <b>Яйцо получено!</b>\n\n"
            f"Теперь высиживай его! Напиши /incubate (нужно 4 раза).\n"
            f"Тип яйца: {player.get('egg_type', 'обычное')}",
            parse_mode="HTML"
        )
    else:
        await message.reply("❌ Ошибка при создании питомца. Попробуй позже.")

async def incubate_cmd(message: types.Message):
    """
    Высиживание яйца питомца.
    
    Увеличивает счетчик прогресса инкубации (inc_progress) на 1 при каждом вызове.
    При достижении лимита прогресса питомец вылупляется (hatched=True).
    
    Args:
        message (types.Message): Сообщение от пользователя, содержит chat.id как идентификатор.
    
    Returns:
        None: Отправляет ответ пользователю через message.reply().
    
    Raises:
        Не генерирует исключений напрямую; ошибки БД обрабатываются внутри.
    """
    # Константы инкубации
    MAX_INC_PROGRESS = 4          # Максимальное количество этапов инкубации
    PROGRESS_INCREMENT = 1        # На сколько увеличивается прогресс за один вызов
    PROGRESS_MIN_VALUE = 0        # Минимальное значение прогресса (для валидации)
    HP_AFTER_HATCH = 100          # Начальное HP после вылупления
    HUNGER_AFTER_HATCH = 50       # Начальный голод после вылупления
    MOOD_AFTER_HATCH = 50         # Начальное настроение после вылупления
    
    user_id = str(message.chat.id)
    
    # Валидация: проверяем тип chat.id
    if not isinstance(message.chat.id, int) or message.chat.id <= 0:
        await message.reply("❌ Некорректный идентификатор пользователя.")
        logger.error(f"Некорректный chat.id: {message.chat.id} (тип: {type(message.chat.id)})")
        return
    
    logger.info(f"Пользователь {user_id} запускает инкубацию.")
    
    # Загружаем данные игрока
    player = get_player(user_id)
    
    # Крайний случай: игрок не найден
    if player is None:
        logger.warning(f"Игрок {user_id} не найден в БД при попытке инкубации.")
        await message.reply("❌ Вы ещё не создали питомца! Используйте /egg.")
        return
    
    # Крайний случай: данные игрока пустые
    if not isinstance(player, dict):
        logger.error(f"Некорректные данные игрока {user_id}: {player}")
        await message.reply("❌ Ошибка загрузки данных. Попробуйте позже.")
        return
    
    # Валидация: проверяем наличие ключевых полей
    required_fields = ['inc_progress', 'hatched']
    for field in required_fields:
        if field not in player:
            logger.error(f"У игрока {user_id} отсутствует поле '{field}'")
            await message.reply("❌ Ошибка данных питомца. Попробуйте /start.")
            return
    
    # Крайний случай: питомец уже вылупился
    if player.get('hatched', False):
        await message.reply("🐣 Ваш питомец уже вылупился! Используйте /start, чтобы увидеть его.")
        logger.info(f"Пользователь {user_id} попытался инкубировать уже вылупившегося питомца.")
        return
    
    # Валидация: inc_progress должен быть числом
    current_progress = player.get('inc_progress', 0)
    if not isinstance(current_progress, (int, float)):
        logger.error(f"Некорректное значение inc_progress у игрока {user_id}: {current_progress}")
        await message.reply("❌ Ошибка данных прогресса. Попробуйте позже.")
        return
    
    # Крайний случай: прогресс меньше минимума (исправляем)
    if current_progress < PROGRESS_MIN_VALUE:
        logger.warning(f"Прогресс инкубации игрока {user_id} был отрицательным: {current_progress}. Сброшен до 0.")
        current_progress = PROGRESS_MIN_VALUE
    
    # Крайний случай: прогресс больше или равен максимуму (уже должен вылупиться)
    if current_progress >= MAX_INC_PROGRESS:
        # Вылупление
        update_data = {
            'hatched': True,
            'inc_progress': MAX_INC_PROGRESS,
            'hp': HP_AFTER_HATCH,
            'hunger': HUNGER_AFTER_HATCH,
            'mood': MOOD_AFTER_HATCH,
        }
        update_player(user_id, update_data)
        
        await message.reply(
            f"🎉 Ваше яйцо вылупилось! Встречайте {player.get('pet_emoji', '🐉')} {player.get('pet_name', 'Питомец')}!\n"
            f"HP: {HP_AFTER_HATCH} | Голод: {HUNGER_AFTER_HATCH} | Настроение: {MOOD_AFTER_HATCH}"
        )
        logger.info(f"Питомец игрока {user_id} вылупился после инкубации (прогресс достиг {MAX_INC_PROGRESS}).")
        return
    
    # Нормальный случай: увеличиваем прогресс
    new_progress = int(current_progress) + PROGRESS_INCREMENT
    
    # Крайний случай: переполнение при сложении
    if new_progress > MAX_INC_PROGRESS:
        logger.warning(f"Прогресс инкубации игрока {user_id} превысил максимум: {new_progress}. Установлен на {MAX_INC_PROGRESS}.")
        new_progress = MAX_INC_PROGRESS
    
    # Обновляем прогресс
    update_player(user_id, {'inc_progress': new_progress})
    
    # Определяем стадию для сообщения пользователю
    stage_messages = {
        1: "🥚 Яйцо начинает нагреваться... (1/4)",
        2: "🐣 Внутри яйца слышно шевеление... (2/4)",
        3: "🐥 Скорлупа покрывается трещинами... (3/4)",
        4: "🎉 Ещё немного, и питомец вылупится! (4/4)",
    }
    stage_text = stage_messages.get(new_progress, f"🥚 Прогресс инкубации: {new_progress}/{MAX_INC_PROGRESS}")
    
    await message.reply(stage_text)
    logger.info(f"Прогресс инкубации игрока {user_id} увеличен: {current_progress} -> {new_progress}.")
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
        f"🍗 Голод: {new_hunger}/100\n😊 Настроение: {new_mood}/100\n❤️ HP: {new_hp}/{player['max_hp']}",
        parse_mode="HTML"
    )

async def train_cmd(message: types.Message):
    uid = str(message.from_user.id)
    player = get_player(uid)
    
    if not player:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return
    
    stats = ["strength", "agility", "magic", "defense", "speed"]
    stat = random.choice(stats)
    boost = random.randint(1, 3)
    
    new_data = {
        stat: player[stat] + boost,
        "xp": player["xp"] + random.randint(10, 30),
        "hunger": max(0, player["hunger"] - random.randint(10, 25)),
        "mood": max(0, player["mood"] - random.randint(5, 10)),
    }
    
    if new_data["xp"] >= player["level"] * 50:
        new_data["level"] = player["level"] + 1
        new_data["xp"] = 0
        new_data["max_hp"] = player["max_hp"] + 15
        new_data["hp"] = new_data["max_hp"]
        level_up = " 🎉 УРОВЕНЬ ПОВЫШЕН!"
    else:
        level_up = ""
    
    update_player(uid, new_data)
    
    stat_names = {"strength": "⚡ Сила", "agility": "💨 Ловкость", "magic": "🔮 Магия", "defense": "🛡️ Защита", "speed": "💫 Скорость"}
    await message.reply(
        f"🏋️ Тренировка завершена!\n{stat_names[stat]}: +{boost}\n"
        f"✨ Опыт: {new_data['xp']}/{player['level'] * 50}\n"
        f"🍗 Голод: {new_data['hunger']}/100\n😊 Настроение: {new_data['mood']}/100{level_up}",
        parse_mode="HTML"
    )

async def battle_cmd(message: types.Message):
    uid = str(message.from_user.id)
    player = get_player(uid)
    
    if not player:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return
    
    opponent = get_random_opponent(uid)
    
    if opponent:
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

async def top_cmd(message: types.Message):
    players = get_top_players(10)
    
    if not players:
        await message.reply("Пока никто не участвовал в битвах!")
        return
    
    lines = ["🏆 <b>ТАБЛИЦА ЛИДЕРОВ</b>\n"]
    for i, p in enumerate(players, 1):
        lines.append(f"{i}. {p.get('pet_emoji', '❓')} {p['pet_name']} — {p['wins']}W/{p['losses']}L, lvl {p['level']}")
    
    await message.reply("\n".join(lines), parse_mode="HTML")

async def stats_cmd(message: types.Message):
    uid = str(message.from_user.id)
    player = get_player(uid)
    
    if not player:
        await message.reply("У тебя нет питомца! Напиши /egg.")
        return
    
    await message.reply(
        f"📊 <b>{player['pet_emoji']} {player['pet_name']}</b>\n"
        f"⭐ Уровень: {player['level']} ({player['xp']}/{player['level']*50} XP)\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
        f"⚡ Сила: {player['strength']}\n💨 Ловкость: {player['agility']}\n"
        f"🔮 Магия: {player['magic']}\n🛡️ Защита: {player['defense']}\n"
        f"💫 Скорость: {player['speed']}\n"
        f"🍗 Голод: {player['hunger']}/100\n😊 Настроение: {player['mood']}/100\n"
        f"🏆 Победы: {player['wins']} | 💀 Поражения: {player['losses']}",
        parse_mode="HTML"
    )

async def help_cmd(message: types.Message):
    await message.reply(
        "🐉 <b>УРОБОРОС: АРЕНА</b>\n\n"
        "🥚 /egg — Получить яйцо\n"
        "🔥 /incubate — Высиживать яйцо (4 раза)\n"
        "🍽 /feed — Покормить питомца\n"
        "🏋️ /train — Тренировать\n"
        "⚔️ /battle — Сразиться на арене\n"
        "🏆 /top — Таблица лидеров\n"
        "📊 /stats — Статистика питомца\n"
        "📝 /report — Сообщить о баге",
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