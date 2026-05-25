# bot.py — Тамагочи-Арена "Уроборос" (Supabase)
"""Вырасти питомца и сразись на арене!"""
import os
import sys
import random
import logging
from pathlib import Path
from datetime import datetime, timezone

from supabase import create_client, Client

import signal
import subprocess

# 🔪 Убиваем все старые экземпляры бота, кроме текущего
current_pid = os.getpid()
try:
    result = subprocess.run(['pgrep', '-f', 'bot.py'], capture_output=True, text=True)
    for pid_str in result.stdout.strip().split('\n'):
        if pid_str and int(pid_str) != current_pid:
            os.kill(int(pid_str), signal.SIGKILL)
            print(f"🔪 Убит старый процесс бота: PID {pid_str}")
except Exception:
    pass

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
    """
    Обработчик команды /egg. Выдаёт игроку яйцо, создавая запись в Supabase.
    
    Аргументы:
        message (types.Message): Сообщение от пользователя с командами.
    
    Возвращает:
        None: Отправляет ответ пользователю через reply.
    
    Логика:
        - Проверяет, существует ли игрок в БД (get_player). Если уже есть — сообщает.
        - Иначе создаёт нового игрока через create_player.
        - Логирует создание нового игрока.
        - Формирует и отправляет сообщение с приветствием и характеристиками питомца.
    """
    # Константы для форматирования сообщения
    EMOJI_EGG = "🥚"
    STATS_SEPARATOR = " | "
    STAT_NAMES = {
        "strength": "⚔️Сила",
        "agility": "💨Ловкость",
        "magic": "🔮Магия",
        "defense": "🛡️Защита",
        "speed": "⚡Скорость",
        "hp": "❤️HP",
        "hunger": "🍖Голод",
        "mood": "😊Настроение",
        "level": "📊Уровень",
        "xp": "⭐Опыт",
        "wins": "🏆Побед",
        "losses": "💀Поражений"
    }
    MAX_HUNGER = 100  # Максимальное значение голода
    MIN_HUNGER = 0    # Минимальное значение голода
    MAX_MOOD = 100    # Максимальное значение настроения
    MIN_MOOD = 0      # Минимальное значение настроения
    
    user_id = str(message.from_user.id)
    logger.info(f"Пользователь {user_id} запросил команду /egg")
    
    # Валидация входных данных
    if not user_id or not user_id.isdigit():
        logger.error(f"Некорректный user_id: {user_id}")
        await message.reply("❌ Ошибка: некорректный идентификатор пользователя.")
        return
    
    try:
        # Проверка существования игрока
        existing_player = get_player(user_id)
        
        # Если игрок уже существует
        if existing_player:
            logger.info(f"Игрок {user_id} уже существует, отказ в выдаче яйца")
            # Проверяем, есть ли у него уже питомец
            if existing_player.get("pet_name"):
                await message.reply(
                    f"🌟 У тебя уже есть питомец {existing_player.get('pet_emoji', EMOJI_EGG)} {existing_player.get('pet_name', 'Безымянный')}! "
                    f"Ты можешь заботиться о нём через команды и сражаться в /battle.",
                    parse_mode="HTML"
                )
            else:
                await message.reply(
                    f"{EMOJI_EGG} У тебя уже есть яйцо! Используй /incubate, чтобы высидеть его.",
                    parse_mode="HTML"
                )
            return
        
        # Создание нового игрока
        logger.info(f"Создание нового игрока {user_id}")
        new_player = create_player(user_id)
        
        # Проверка успешности создания
        if not new_player:
            logger.error(f"Не удалось создать игрока {user_id} в Supabase")
            await message.reply(
                "❌ Ошибка при создании питомца. Пожалуйста, попробуй позже.",
                parse_mode="HTML"
            )
            return
        
        # Валидация данных нового игрока
        required_keys = ["pet_name", "pet_emoji", "hp", "max_hp", "strength", "agility", 
                        "magic", "defense", "speed", "hunger", "mood", "level", "xp", "wins", "losses"]
        for key in required_keys:
            if key not in new_player:
                logger.error(f"У нового игрока {user_id} отсутствует поле {key}")
                await message.reply(
                    "❌ Ошибка: некорректные данные питомца. Попробуй создать питомца снова.",
                    parse_mode="HTML"
                )
                return
        
        # Обработка крайних случаев для числовых значений
        hunger = max(MIN_HUNGER, min(MAX_HUNGER, new_player.get("hunger", 50)))
        mood = max(MIN_MOOD, min(MAX_MOOD, new_player.get("mood", 50)))
        hp = max(0, min(new_player.get("max_hp", 100), new_player.get("hp", 100)))
        
        # Формирование сообщения с характеристиками питомца
        pet_name = new_player["pet_name"]
        pet_emoji = new_player["pet_emoji"]
        
        # Сборка строки характеристик
        stats_lines = []
        
        # Основные характеристики
        basic_stats = [
            f"{STAT_NAMES['hp']} {hp}/{new_player.get('max_hp', 100)}",
            f"{STAT_NAMES['hunger']} {hunger}/{MAX_HUNGER}",
            f"{STAT_NAMES['mood']} {mood}/{MAX_MOOD}",
            f"{STAT_NAMES['level']} {new_player.get('level', 1)}",
            f"{STAT_NAMES['xp']} {new_player.get('xp', 0)}"
        ]
        stats_lines.append("📊 <b>Основное:</b>")
        stats_lines.append(STATS_SEPARATOR.join(basic_stats))
        
        # Боевые характеристики
        battle_stats = [
            f"{STAT_NAMES['strength']} {new_player.get('strength', 0)}",
            f"{STAT_NAMES['agility']} {new_player.get('agility', 0)}",
            f"{STAT_NAMES['magic']} {new_player.get('magic', 0)}",
            f"{STAT_NAMES['defense']} {new_player.get('defense', 0)}",
            f"{STAT_NAMES['speed']} {new_player.get('speed', 0)}"
        ]
        stats_lines.append("⚔️ <b>Боевые:</b>")
        stats_lines.append(STATS_SEPARATOR.join(battle_stats))
        
        # Статистика
        statistics = [
            f"{STAT_NAMES['wins']} {new_player.get('wins', 0)}",
            f"{STAT_NAMES['losses']} {new_player.get('losses', 0)}"
        ]
        stats_lines.append("🏅 <b>Статистика:</b>")
        stats_lines.append(STATS_SEPARATOR.join(statistics))
        
        # Формирование итогового сообщения
        message_text = (
            f"🎉 <b>Поздравляю, {message.from_user.first_name}!</b>\n\n"
            f"{EMOJI_EGG} Ты получил яйцо! Высиживай его командой /incubate.\n\n"
            f"🐣 Из яйца вылупится <b>{pet_emoji} {pet_name}</b>!\n\n"
            f"{chr(10).join(stats_lines)}\n\n"
            f"💡 <i>Подсказка: используй /help для просмотра всех команд.</i>"
        )
        
        logger.info(f"Новый игрок {user_id} успешно создан с питомцем {pet_name}")
        await message.reply(message_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке /egg для пользователя {user_id}: {e}")
        await message.reply(
            "❌ Произошла неожиданная ошибка. Пожалуйста, попробуй позже.",
            parse_mode="HTML"
        )
async def incubate_cmd(message: types.Message):
    """Инкубирует яйцо питомца, увеличивая прогресс инкубации.
    
    Args:
        message: Сообщение от пользователя с командой /incubate
        
    Returns:
        None. Отправляет ответ пользователю с результатом инкубации.
    """
    uid = str(message.from_user.id)
    player = get_player(uid)
    
    if not player:
        await message.reply("❌ Сначала создай питомца через /start!")
        return
    
    # Константы
    INCUBATE_COOLDOWN_MINUTES = 60
    INCUBATE_PROGRESS_INCREMENT = 25
    MAX_INCUBATION_PROGRESS = 100
    HUNGER_DECREASE = 10
    
    # Проверка кулдауна
    last_incubate_time = player.get("last_incubate_time")
    if last_incubate_time:
        try:
            last_time = datetime.fromisoformat(last_incubate_time)
            time_diff = datetime.now(timezone.utc) - last_time
            minutes_passed = time_diff.total_seconds() / 60
            
            if minutes_passed < INCUBATE_COOLDOWN_MINUTES:
                remaining_minutes = int(INCUBATE_COOLDOWN_MINUTES - minutes_passed)
                await message.reply(
                    f"⏳ Яйцо ещё не готово к инкубации! Подожди {remaining_minutes} мин."
                )
                return
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка парсинга last_incubate_time: {e}")
    
    # Проверка, вылупился ли уже питомец
    if player.get("hatched", False):
        await message.reply("🥚 Твой питомец уже вылупился! Используй /feed, /train или /battle.")
        return
    
    # Проверка голода
    hunger = player.get("hunger", 100)
    if hunger <= 0:
        await message.reply("😴 Питомец слишком голоден для инкубации! Покорми его /feed.")
        return
    
    # Инкубация
    current_progress = player.get("inc_progress", 0)
    new_progress = min(current_progress + INCUBATE_PROGRESS_INCREMENT, MAX_INCUBATION_PROGRESS)
    
    # Обновление данных
    update_data = {
        "inc_progress": new_progress,
        "hunger": max(0, hunger - HUNGER_DECREASE),
        "last_incubate_time": datetime.now(timezone.utc).isoformat()
    }
    
    update_player(uid, update_data)
    logger.info(f"Игрок {uid} инкубировал яйцо: прогресс {new_progress}%")
    
    # Проверка вылупления
    if new_progress >= MAX_INCUBATION_PROGRESS:
        # Вылупление питомца
        hatch_data = {
            "hatched": True,
            "inc_progress": MAX_INCUBATION_PROGRESS,
            "hp": player.get("max_hp", 100),
            "mood": "счастлив"
        }
        update_player(uid, hatch_data)
        
        pet_name = player.get("pet_name", "Питомец")
        pet_emoji = player.get("pet_emoji", "🐉")
        
        await message.reply(
            f"🎉 *ПОЗДРАВЛЯЮ!* 🎉\n\n"
            f"{pet_emoji} *{pet_name}* вылупился из яйца!\n\n"
            f"Теперь ты можешь:\n"
            f"🍖 /feed — покормить питомца\n"
            f"💪 /train — тренировать питомца\n"
            f"⚔️ /battle — сразиться на арене\n"
            f"📊 /stats — посмотреть статистику",
            parse_mode="Markdown"
        )
    else:
        await message.reply(
            f"🥚 Инкубация яйца...\n\n"
            f"📊 Прогресс: {new_progress}%\n"
            f"🍽️ Сытость: {max(0, hunger - HUNGER_DECREASE)}%\n\n"
            f"Продолжай инкубировать, чтобы питомец вылупился!"
        )
async def feed_cmd(message: types.Message):
    """
    Обрабатывает команду /feed — кормление питомца.
    Восстанавливает голод, HP и настроение в зависимости от текущего состояния.
    
    Параметры:
        message (types.Message): сообщение от пользователя с командой /feed
        
    Возвращаемое значение:
        None (отправляет ответное сообщение через message.reply)
        
    Логирование:
        - INFO: успешное кормление
        - WARNING: кормление при нулевом голоде
        - ERROR: ошибки БД или валидации
    """
    # Константы для регулировки кормления
    HUNGER_RESTORE = 30
    HP_RESTORE = 10
    MOOD_RESTORE = 15
    MAX_HUNGER = 100
    MAX_MOOD = 100
    MIN_HUNGER_FOR_FEED = 5  # не кормим если голод < 5 (почти сыт)
    
    uid = str(message.from_user.id)
    
    # 1. Валидация: проверяем существование игрока
    player = get_player(uid)
    if player is None:
        logger.warning(f"Попытка кормления несуществующего игрока: {uid}")
        await message.reply("❌ <b>Ты ещё не создал питомца!</b>\nНапиши /egg, чтобы получить яйцо.")
        return
    
    # 2. Проверка: вылупился ли питомец
    if not player.get("hatched", False):
        logger.info(f"Кормление яйца игроком {uid} — отказ (ещё не вылупилось)")
        await message.reply("🥚 <b>Твой питомец ещё в яйце!</b>\nИспользуй /incubate, чтобы высидеть его.")
        return
    
    # 3. Проверка на крайний случай: голод уже на минимуме
    current_hunger = player.get("hunger", 0)
    if current_hunger < MIN_HUNGER_FOR_FEED:
        logger.info(f"Питомец {player.get('pet_name', '?')} (id={uid}) уже сыт, голод={current_hunger}")
        await message.reply(
            f"🍖 <b>{player.get('pet_emoji', '🐉')} {player.get('pet_name', 'Питомец')}</b> уже сыт! "
            f"Голод: {current_hunger}/{MAX_HUNGER}."
        )
        return
    
    # 4. Вычисляем новые значения с ограничениями
    new_hunger = min(current_hunger + HUNGER_RESTORE, MAX_HUNGER)
    
    current_hp = player.get("hp", 0)
    max_hp = player.get("max_hp", 100)
    new_hp = min(current_hp + HP_RESTORE, max_hp)
    
    current_mood = player.get("mood", 0)
    new_mood = min(current_mood + MOOD_RESTORE, MAX_MOOD)
    
    # 5. Логирование и обновление
    pet_name = player.get("pet_name", "Питомец")
    pet_emoji = player.get("pet_emoji", "🐉")
    
    update_data = {
        "hunger": new_hunger,
        "hp": new_hp,
        "mood": new_mood
    }
    
    try:
        update_player(uid, update_data)
        logger.info(
            f"Кормление питомца {pet_name} (id={uid}): "
            f"голод {current_hunger}→{new_hunger}, "
            f"HP {current_hp}→{new_hp}, "
            f"настроение {current_mood}→{new_mood}"
        )
    except Exception as e:
        logger.error(f"Ошибка обновления БД при кормлении игрока {uid}: {e}")
        await message.reply("❌ <b>Ошибка базы данных!</b>\nПопробуй ещё раз.")
        return
    
    # 6. Формируем ответ
    response_parts = [
        f"🍖 <b>{pet_emoji} {pet_name}</b> с удовольствием поел!",
        "",
        f"❤️ HP: {current_hp} → {new_hp}/{max_hp}",
        f"🍞 Голод: {current_hunger} → {new_hunger}/{MAX_HUNGER}",
        f"😊 Настроение: {current_mood} → {new_mood}/{MAX_MOOD}"
    ]
    
    if new_hunger >= MAX_HUNGER:
        response_parts.append(f"\n🥴 {pet_emoji} {pet_name} объелся! Больше не влезет.")
    
    await message.reply("\n".join(response_parts))
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