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

def get_player_by_username(username: str) -> dict | None:
    """Ищет игрока по username в Supabase."""
    if not supabase:
        return None
    try:
        # Убираем @ если есть
        clean_username = username.replace('@', '').strip()
        response = supabase.table("players").select("*").eq("username", clean_username).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Ошибка поиска игрока по username: {e}")
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
        # Сохраняем username если его нет
        if not player.get("username") and message.from_user.username:
            update_player(uid, {"username": message.from_user.username})

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
    Обрабатывает команду /egg — выдаёт игроку яйцо нового питомца.
    
    Если игрок уже существует, команда не срабатывает (повторное яйцо не выдаётся).
    Создаёт запись игрока в Supabase с начальными характеристиками.
    
    Параметры:
        message (types.Message): Сообщение от пользователя с командой /egg
        
    Возвращает:
        None: Отправляет ответное сообщение с результатом
    """
    # Константы для валидации
    EMPTY_NAME = "безымянный"
    EGG_GIVEN_MESSAGE = "🥚 Ты получил яйцо! Используй /incubate, чтобы высидеть питомца."
    ALREADY_HAS_EGG_MESSAGE = "🌟 У тебя уже есть питомец! Используй /start, чтобы увидеть его."
    ERROR_MESSAGE = "⚠️ Ошибка создания. Попробуй позже."
    
    # Получаем ID пользователя
    user_id = message.from_user.id
    logger.info(f"Команда /egg от пользователя {user_id}")
    
    # Проверяем, существует ли уже игрок в БД
    existing_player = get_player(str(user_id))
    
    if existing_player:
        logger.info(f"Пользователь {user_id} уже имеет питомца")
        await message.reply(ALREADY_HAS_EGG_MESSAGE)
        return
    
    # Проверяем, что данные пользователя не None
    if message.from_user is None:
        logger.error("Ошибка: message.from_user равен None")
        await message.reply(ERROR_MESSAGE)
        return
    
    # Создаём нового игрока
    new_player = create_player(str(user_id))
    
    if new_player is None:
        logger.error(f"Не удалось создать игрока {user_id} в Supabase")
        await message.reply(ERROR_MESSAGE)
        return
    
    # Проверяем, что все ключевые поля существуют
    required_fields = ['pet_name', 'pet_emoji', 'hp', 'max_hp']
    for field in required_fields:
        if field not in new_player:
            logger.error(f"У нового игрока {user_id} отсутствует поле {field}")
            await message.reply(ERROR_MESSAGE)
            return
    
    # Проверяем крайние случаи: если имя питомца пустое
    pet_name = new_player.get('pet_name', '').strip()
    if not pet_name:
        logger.warning(f"У игрока {user_id} пустое имя питомца, устанавливаем '{EMPTY_NAME}'")
        update_player(str(user_id), {'pet_name': EMPTY_NAME})
        new_player['pet_name'] = EMPTY_NAME
    
    # Логируем успешное создание
    logger.info(f"Создан новый игрок {user_id} (питомец: {new_player.get('pet_name', 'неизвестно')})")
    
    # Отправляем ответ
    await message.reply(EGG_GIVEN_MESSAGE)
async def incubate_cmd(message: types.Message):
    """
    Обрабатывает команду /incubate - инкубация яйца питомца.
    
    Проверяет наличие яйца у игрока, запускает процесс инкубации
    с прогрессом, увеличивающимся при каждом вызове.
    После достижения 100% яйцо вылупляется и создается питомец.
    
    Args:
        message: Объект сообщения от пользователя
        
    Returns:
        None: Отправляет ответ пользователю через reply
    """
    try:
        user_id = str(message.from_user.id)
        player = get_player(user_id)
        
        if not player:
            # Создаем нового игрока с яйцом
            player = create_player(user_id)
            if not player:
                await message.reply("❌ Не удалось создать профиль. Попробуйте позже.")
                return
            await message.reply("🥚 Вы получили яйцо! Используйте /incubate чтобы начать инкубацию.")
            return
        
        # Проверяем, не вылупился ли уже питомец
        if player.get("hatched", False):
            await message.reply(f"🐣 Ваш питомец {player.get('pet_emoji', '')} {player.get('pet_name', '')} уже вылупился! Используйте /stats для просмотра.")
            return
        
        # Проверяем наличие яйца
        if not player.get("egg_type"):
            await message.reply("🥚 У вас нет яйца! Используйте /egg чтобы получить новое.")
            return
        
        # Получаем текущий прогресс инкубации
        current_progress = player.get("inc_progress", 0)
        
        # Проверяем, не завершена ли инкубация
        if current_progress >= 100:
            # Вылупляем питомца
            pet = random_pet()
            update_data = {
                "hatched": True,
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
                "inc_progress": 0,
                "egg_type": None
            }
            update_player(user_id, update_data)
            
            await message.reply(
                f"🎉 Яйцо вылупилось!\n\n"
                f"Поздравляю! У вас появился питомец:\n"
                f"{pet['emoji']} {pet['name']}\n\n"
                f"Характеристики:\n"
                f"❤️ HP: {pet['hp']}/{pet['max_hp']}\n"
                f"⚔️ Сила: {pet['strength']}\n"
                f"💨 Ловкость: {pet['agility']}\n"
                f"🔮 Магия: {pet['magic']}\n"
                f"🛡️ Защита: {pet['defense']}\n"
                f"🏃 Скорость: {pet['speed']}\n\n"
                f"Используйте /stats для просмотра полной информации!"
            )
            return
        
        # Увеличиваем прогресс инкубации
        progress_increment = random.randint(10, 25)
        new_progress = min(current_progress + progress_increment, 100)
        
        # Обновляем прогресс в базе данных
        update_player(user_id, {"inc_progress": new_progress})
        
        # Создаем визуальный прогресс-бар
        progress_bar_length = 10
        filled_length = int(progress_bar_length * new_progress / 100)
        progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
        
        # Определяем стадию инкубации
        if new_progress < 30:
            stage = "🌱 Яйцо только начинает нагреваться..."
            emoji = "🥚"
        elif new_progress < 60:
            stage = "🌿 Внутри яйца чувствуется движение!"
            emoji = "🥚✨"
        elif new_progress < 90:
            stage = "🌺 Яйцо светится и вибрирует!"
            emoji = "🥚🌟"
        else:
            stage = "🔥 Яйцо вот-вот вылупится!"
            emoji = "🥚💫"
        
        # Формируем сообщение о прогрессе
        progress_message = (
            f"{emoji} Инкубация яйца\n\n"
            f"{stage}\n\n"
            f"Прогресс: {new_progress}%\n"
            f"[{progress_bar}]\n\n"
            f"💡 Используйте /incubate снова чтобы продолжить инкубацию!"
        )
        
        await message.reply(progress_message)
        
    except Exception as e:
        logger.error(f"Ошибка в incubate_cmd для пользователя {message.from_user.id}: {e}")
        await message.reply("❌ Произошла ошибка при инкубации. Попробуйте позже.")
async def feed_cmd(message: types.Message):
    """Кормит питомца: восстанавливает голод (0-100), HP и настроение.
    
    Обрабатывает команду /feed.
    Требует, чтобы питомец уже был создан (высижен).
    Использует кулдаун в 60 секунд между кормлениями.
    
    Args:
        message (types.Message): Сообщение от пользователя с командой /feed.
        
    Returns:
        None: Отправляет ответное сообщение через message.reply().
        
    Raises:
        Exception: Ловится внутри, ошибки логируются.
    """
    # Константы для кормления
    FEED_HUNGER_REDUCTION = 35  # На сколько снижается голод
    FEED_HP_RECOVERY = 15       # На сколько восстанавливается HP
    FEED_MOOD_BONUS = 10        # На сколько повышается настроение
    MAX_HUNGER = 100            # Максимальный уровень голода (0 = сыт)
    MAX_MOOD = 100              # Максимальное настроение
    MIN_VALUE = 0               # Минимальное значение для всех статов
    COOLDOWN_SECONDS = 60       # Кулдаун между кормлениями в секундах

    user_id = str(message.from_user.id)
    logger.info(f"Пользователь {user_id} вызвал /feed")

    # Валидация: проверяем, существует ли игрок в БД
    player = get_player(user_id)
    if player is None:
        logger.warning(f"Пользователь {user_id} не найден в БД при вызове /feed")
        await message.reply("❌ <b>Ты ещё не создал питомца!</b>\nИспользуй /egg, чтобы получить яйцо.")
        return

    # Проверяем, высижено ли яйцо (питомец готов к уходу)
    if not player.get("hatched", False):
        logger.info(f"Пользователь {user_id} пытается покормить невысиженное яйцо")
        await message.reply("🥚 <b>Твоё яйцо ещё не высижено!</b>\nИспользуй /incubate, чтобы высидеть его.")
        return

    # Rate limiting: проверяем время последнего кормления
    last_feed_str = player.get("last_feed", None)
    if last_feed_str:
        try:
            last_feed_dt = datetime.fromisoformat(last_feed_str)
            now = datetime.now(timezone.utc)
            elapsed_seconds = (now - last_feed_dt).total_seconds()
            if elapsed_seconds < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - elapsed_seconds)
                logger.info(f"Пользователь {user_id}: кулдаун кормления ещё не истёк (осталось {remaining}с)")
                await message.reply(
                    f"⏳ <b>Подожди немного!</b>\n"
                    f"Питомца можно кормить раз в {COOLDOWN_SECONDS} секунд.\n"
                    f"Осталось <b>{remaining}</b> секунд."
                )
                return
        except ValueError as e:
            logger.error(f"Ошибка парсинга last_feed для {user_id}: {e}")
            # Если дата кривая, просто продолжаем (без кулдауна)

    # Текущие значения питомца (с обработкой крайних случаев)
    current_hunger = player.get("hunger", MAX_HUNGER)
    current_hp = player.get("hp", 0)
    current_max_hp = player.get("max_hp", 100)
    current_mood = player.get("mood", MAX_MOOD // 2)
    pet_emoji = player.get("pet_emoji", "🐉")
    pet_name = player.get("pet_name", "Питомец")

    # Обработка крайних случаев: если голод уже на минимуме (0 = сыт)
    if current_hunger <= MIN_VALUE:
        logger.info(f"Пользователь {user_id}: попытка кормления сытого питомца")
        await message.reply(f"🍔 <b>{pet_emoji} {pet_name} уже сыт!</b>\nЕму пока не нужно есть.")
        return

    # Обработка крайних случаев: если HP ушло в минус (например, после битвы)
    if current_hp < MIN_VALUE:
        logger.warning(f"Пользователь {user_id}: HP питомца было отрицательным ({current_hp}). Сбрасываем до 0.")
        current_hp = MIN_VALUE

    # Вычисляем новые значения с защитой от выхода за границы
    new_hunger = max(MIN_VALUE, current_hunger - FEED_HUNGER_REDUCTION)
    new_hp = min(current_max_hp, current_hp + FEED_HP_RECOVERY)
    new_mood = min(MAX_MOOD, current_mood + FEED_MOOD_BONUS)

    # Подготавливаем данные для обновления
    update_data = {
        "hunger": new_hunger,
        "hp": new_hp,
        "mood": new_mood,
        "last_feed": datetime.now(timezone.utc).isoformat(),
    }

    # Обновляем в БД
    try:
        update_player(user_id, update_data)
        logger.info(
            f"Пользователь {user_id} покормил питомца: "
            f"голод {current_hunger}->{new_hunger}, "
            f"HP {current_hp}->{new_hp}, "
            f"настроение {current_mood}->{new_mood}"
        )
    except Exception as e:
        logger.error(f"Не удалось обновить данные после кормления для {user_id}: {e}")
        await message.reply("❌ <b>Произошла ошибка при кормлении.</b>\nПопробуй позже.")
        return

    # Формируем ответ пользователю
    # Локализованные сообщения в зависимости от результатов
    hunger_status = "😋 Сытый!" if new_hunger <= 20 else "🤤 Ещё хочет есть."
    hp_status = "❤️ Здоровье восстановлено!" if new_hp == current_max_hp else f"❤️ +{FEED_HP_RECOVERY} HP"
    mood_status = "😊 Счастлив!" if new_mood == MAX_MOOD else f"😃 +{FEED_MOOD_BONUS} к настроению"

    response_text = (
        f"🍔 <b>{pet_emoji} {pet_name} покормлен!</b>\n\n"
        f"🥩 <b>Голод:</b> {new_hunger}/100 ({hunger_status})\n"
        f"{hp_status}\n"
        f"{mood_status}\n\n"
        f"💪 Хороший уход делает питомца сильнее!"
    )

    await message.reply(response_text)
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
    """Обрабатывает команду /battle для дуэли с другим игроком.
    
    Проверяет состояние питомца, наличие противника, проводит бой и обновляет статистику.
    После победы с шансом 30% выпадает аптечка.
    
    Args:
        message: Объект сообщения от aiogram
        
    Returns:
        None
    """
    MIN_HP_FOR_BATTLE = 1
    KNOCKOUT_HP = 0
    HEAL_CHANCE = 0.3
    HEAL_AMOUNT = 50
    
    uid = str(message.from_user.id)
    player = get_player(uid)
    
    if not player:
        await message.reply("❌ Ты ещё не создал питомца! Напиши /start")
        return
    
    if player.get("hp", 0) <= KNOCKOUT_HP:
        await message.reply("💀 Твой питомец без сознания! Используй /use аптечка, чтобы восстановить его.")
        return
    
    if player.get("hp", 0) < MIN_HP_FOR_BATTLE:
        await message.reply("💀 Твой питомец слишком слаб для боя! Покорми его /feed или используй аптечку.")
        return
    
    args = message.get_args()
    if not args:
        await message.reply("⚔️ Укажи противника: /battle @username")
        return
    
    target_username = args.strip()
    if not target_username.startswith('@'):
        target_username = '@' + target_username
    
    try:
        target_player = get_player_by_username(target_username)
        if not target_player:
            await message.reply(f"❌ Игрок {target_username} не найден. Попроси его написать /start боту.")
            return
        target_uid = str(target_player["user_id"])
    except Exception as e:
        logger.error(f"Ошибка поиска пользователя: {e}")
        await message.reply(f"❌ Не удалось найти игрока {target_username}.")
        return
    
    target_uid = str(chat_member.user.id)
    
    if target_uid == uid:
        await message.reply("🤦 Нельзя сражаться с самим собой!")
        return
    
    target_player = get_player(target_uid)
    
    if not target_player:
        await message.reply(f"❌ Игрок {target_username} ещё не активировал питомца. Попроси его написать /start боту в личные сообщения.")
        return
    
    if target_player.get("hp", 0) <= KNOCKOUT_HP:
        await message.reply(f"💀 Питомец {target_username} без сознания! Он не может сражаться.")
        return
    
    if target_player.get("hp", 0) < MIN_HP_FOR_BATTLE:
        await message.reply(f"💀 Питомец {target_username} слишком слаб для боя!")
        return
    
    # Расчет урона
    player_attack = player.get("strength", 5) + player.get("magic", 3)
    target_defense = target_player.get("defense", 3)
    target_speed = target_player.get("speed", 5)
    
    # Базовая механика боя
    damage = max(1, player_attack - target_defense // 2)
    
    # Шанс критического удара
    crit_chance = player.get("agility", 5) / 100
    if random.random() < crit_chance:
        damage = int(damage * 1.5)
        crit_text = " 💥 КРИТИЧЕСКИЙ УДАР!"
    else:
        crit_text = ""
    
    # Шанс уклонения
    dodge_chance = target_speed / 100
    if random.random() < dodge_chance:
        await message.reply(f"⚔️ {player.get('pet_emoji', '🐉')} {player.get('pet_name', 'Питомец')} атакует {target_username}!\n"
                          f"🔄 {target_username} уклонился от атаки!")
        return
    
    # Нанесение урона
    new_hp = max(KNOCKOUT_HP, target_player.get("hp", 100) - damage)
    
    # Проверка нокаута
    if new_hp <= KNOCKOUT_HP:
        new_hp = KNOCKOUT_HP
        knockout_text = "\n💀 ПРОТИВНИК В НОКАУТЕ!"
    else:
        knockout_text = ""
    
    # Обновление статистики
    target_data = {"hp": new_hp}
    player_data = {}
    
    if new_hp <= KNOCKOUT_HP:
        # Победа
        player_data["wins"] = player.get("wins", 0) + 1
        player_data["xp"] = player.get("xp", 0) + 20
        target_data["losses"] = target_player.get("losses", 0) + 1
        
        # Шанс выпадения аптечки
        if random.random() < HEAL_CHANCE:
            inventory = player.get("inventory", {})
            if isinstance(inventory, str):
                try:
                    import json
                    inventory = json.loads(inventory)
                except:
                    inventory = {}
            
            if "аптечка" not in inventory:
                inventory["аптечка"] = 0
            inventory["аптечка"] += 1
            player_data["inventory"] = inventory
            
            heal_drop_text = "\n🎁 Выпала аптечка!"
        else:
            heal_drop_text = ""
        
        # Проверка уровня
        if player_data.get("xp", 0) >= player.get("level", 1) * 50:
            player_data["level"] = player.get("level", 1) + 1
            player_data["xp"] = 0
            player_data["max_hp"] = player.get("max_hp", 100) + 10
            player_data["hp"] = player.get("max_hp", 100) + 10
            level_up_text = "\n🌟 УРОВЕНЬ ПОВЫШЕН!"
        else:
            level_up_text = ""
    else:
        # Поражение
        player_data["losses"] = player.get("losses", 0) + 1
        target_data["wins"] = target_player.get("wins", 0) + 1
        target_data["xp"] = target_player.get("xp", 0) + 10
        heal_drop_text = ""
        level_up_text = ""
    
    # Обновление данных
    update_player(uid, player_data)
    update_player(target_uid, target_data)
    
    # Формирование ответа
    response = (
        f"⚔️ ДУЭЛЬ!\n"
        f"{player.get('pet_emoji', '🐉')} {player.get('pet_name', 'Питомец')} VS {target_username}\n\n"
        f"💥 Урон: {damage}{crit_text}{knockout_text}\n"
        f"❤️ HP {target_username}: {target_player.get('hp', 100)} → {new_hp}\n"
        f"{heal_drop_text}"
        f"{level_up_text}"
    )
    
    await message.reply(response)
    logger.info(f"Бой: {uid} vs {target_uid}, урон: {damage}")
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