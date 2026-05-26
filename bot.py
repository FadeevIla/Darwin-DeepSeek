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
    """Инкубация яйца питомца.
    
    Позволяет игроку высиживать яйцо, увеличивая прогресс инкубации.
    При достижении 100% яйцо вылупляется, и питомец становится активным.
    
    Args:
        message: Объект сообщения от пользователя
        
    Returns:
        None: Отправляет ответ пользователю через reply
    """
    # Константы
    INCUBATION_STEP = 10  # Шаг прогресса за одну инкубацию
    MAX_PROGRESS = 100    # Максимальный прогресс инкубации
    COOLDOWN_SECONDS = 300  # Кулдаун между инкубациями (5 минут)
    
    user_id = str(message.from_user.id)
    
    try:
        player = get_player(user_id)
        if not player:
            await message.reply("❌ Ты ещё не создал питомца! Напиши /start")
            return
        
        # Проверка, не вылупился ли уже питомец
        if player.get("hatched", False):
            await message.reply("🐣 Твой питомец уже вылупился! Используй /feed, /train, /battle")
            return
        
        # Проверка кулдауна
        last_incubate = player.get("last_incubate_at")
        if last_incubate:
            try:
                last_time = datetime.fromisoformat(last_incubate)
                now = datetime.now(timezone.utc)
                elapsed = (now - last_time).total_seconds()
                
                if elapsed < COOLDOWN_SECONDS:
                    remaining = int(COOLDOWN_SECONDS - elapsed)
                    minutes = remaining // 60
                    seconds = remaining % 60
                    await message.reply(
                        f"⏳ Подожди ещё {minutes} мин {seconds} сек перед следующей инкубацией!\n"
                        f"Текущий прогресс: {player.get('inc_progress', 0)}%"
                    )
                    return
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка парсинга времени инкубации: {e}")
        
        # Увеличиваем прогресс инкубации
        current_progress = player.get("inc_progress", 0)
        new_progress = min(current_progress + INCUBATION_STEP, MAX_PROGRESS)
        
        update_data = {
            "inc_progress": new_progress,
            "last_incubate_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Проверка на вылупление
        if new_progress >= MAX_PROGRESS:
            update_data["hatched"] = True
            update_data["inc_progress"] = MAX_PROGRESS
            
            update_player(user_id, update_data)
            
            pet_name = player.get("pet_name", "Питомец")
            pet_emoji = player.get("pet_emoji", "🐉")
            
            await message.reply(
                f"🎉 **ЯЙЦО ВЫЛУПИЛОСЬ!**\n\n"
                f"{pet_emoji} **{pet_name}** появился на свет!\n"
                f"Теперь ты можешь:\n"
                f"🍖 /feed — покормить питомца\n"
                f"💪 /train — тренировать питомца\n"
                f"⚔️ /battle — сразиться на арене\n"
                f"📊 /stats — посмотреть характеристики"
            )
            logger.info(f"Игрок {user_id} вылупил питомца {pet_name}")
        else:
            update_player(user_id, update_data)
            
            # Создаем визуальный прогресс-бар
            progress_bar_length = 10
            filled = int(new_progress / MAX_PROGRESS * progress_bar_length)
            empty = progress_bar_length - filled
            progress_bar = "🟢" * filled + "⚪" * empty
            
            await message.reply(
                f"🥚 **Инкубация яйца**\n\n"
                f"Прогресс: {new_progress}%\n"
                f"{progress_bar}\n\n"
                f"Осталось: {MAX_PROGRESS - new_progress}%\n"
                f"Следующая инкубация через 5 минут"
            )
            logger.info(f"Игрок {user_id} инкубировал яйцо: {new_progress}%")
            
    except Exception as e:
        logger.error(f"Ошибка в incubate_cmd для пользователя {user_id}: {e}", exc_info=True)
        await message.reply("❌ Произошла ошибка при инкубации. Попробуй позже.")
async def feed_cmd(message: types.Message):
    """
    Кормление питомца.
    Восстанавливает голод, HP и настроение.
    Использует константы для лимитов и приростов.
    Валидирует состояние игрока и крайние случаи.
    
    Параметры:
        message (types.Message): сообщение от пользователя с командой /feed
        
    Возвращает:
        None: отправляет ответ пользователю через message.reply
    """
    # Константы кормления
    HUNGER_RECOVERY = 25       # восстановление сытости
    HP_RECOVERY = 10           # восстановление здоровья
    MOOD_RECOVERY = 8          # восстановление настроения
    MAX_HUNGER = 100           # максимальная сытость
    MIN_HUNGER = 0             # минимальная сытость
    MIN_HP = 0                 # минимальное HP
    MIN_MOOD = 0               # минимальное настроение
    MAX_MOOD = 100             # максимальное настроение

    user_id = str(message.from_user.id)
    logger.info(f"Команда /feed от пользователя {user_id}")

    # Валидация: игрок должен существовать
    player = get_player(user_id)
    if player is None:
        logger.warning(f"Попытка кормления без питомца: {user_id}")
        await message.reply("❌ У тебя нет питомца! Используй /egg чтобы создать яйцо.")
        return

    # Валидация: питомец должен быть высижен
    if not player.get("hatched", False):
        logger.warning(f"Попытка кормления невысиженного питомца: {user_id}")
        await message.reply("🥚 Сначала высиди яйцо командой /incubate!")
        return

    # Обработка крайних случаев: ограничение значений
    current_hunger = max(MIN_HUNGER, player.get("hunger", 0))
    current_hp = max(MIN_HP, player.get("hp", 0))
    current_mood = max(MIN_MOOD, player.get("mood", 0))
    current_max_hp = player.get("max_hp", 100)

    # Рассчитываем новые значения с учётом максимумов
    new_hunger = min(MAX_HUNGER, current_hunger + HUNGER_RECOVERY)
    new_hp = min(current_max_hp, current_hp + HP_RECOVERY)
    new_mood = min(MAX_MOOD, current_mood + MOOD_RECOVERY)

    # Валидация: проверка что значения изменились (не достигли максимума)
    if (new_hunger == current_hunger and 
        new_hp == current_hp and 
        new_mood == current_mood):
        logger.info(f"Питомец уже сыт и здоров: {user_id}")
        await message.reply(
            f"{player.get('pet_emoji', '🐉')} {player.get('pet_name', 'Питомец')} "
            f"уже полностью сыт, здоров и счастлив!\n"
            f"🍖 Сытость: {current_hunger}/{MAX_HUNGER}\n"
            f"❤️ HP: {current_hp}/{current_max_hp}\n"
            f"😊 Настроение: {current_mood}/{MAX_MOOD}"
        )
        return

    # Обновляем данные питомца
    try:
        update_player(user_id, {
            "hunger": new_hunger,
            "hp": new_hp,
            "mood": new_mood
        })
        
        logger.info(
            f"Питомец накормлен: {user_id} | "
            f"сытость {current_hunger}->{new_hunger}, "
            f"HP {current_hp}->{new_hp}, "
            f"настроение {current_mood}->{new_mood}"
        )
        
        await message.reply(
            f"🍖 {player.get('pet_emoji', '🐉')} *{player.get('pet_name', 'Питомец')}* накормлен!\n\n"
            f"🍽 Сытость: {current_hunger} → {new_hunger}\n"
            f"❤️ HP: {current_hp} → {new_hp}\n"
            f"😊 Настроение: {current_mood} → {new_mood}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении данных кормления: {e}")
        await message.reply("❌ Произошла ошибка при кормлении. Попробуй позже.")
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

async def incubate_cmd(message: types.Message):
    """Инкубирует яйцо питомца. Игрок нажимает команду, прогресс увеличивается на 10%.
    При достижении 100% яйцо вылупляется, и питомец становится активным.
    
    Args:
        message: Сообщение от пользователя с командой /incubate
        
    Returns:
        None: Отправляет ответ пользователю через reply
    """
    MAX_PROGRESS = 100
    INCUBATE_STEP = 10
    MIN_LEVEL_FOR_INCUBATE = 1
    
    user_id = str(message.from_user.id)
    
    try:
        player = get_player(user_id)
    except Exception as e:
        logger.error(f"Ошибка получения данных игрока {user_id}: {e}")
        await message.reply("❌ Ошибка базы данных. Попробуй позже.")
        return
    
    if not player:
        await message.reply("❌ У тебя нет питомца! Создай его через /start")
        return
    
    if player.get("hatched", False):
        await message.reply("🐣 Твой питомец уже вылупился! Не нужно инкубировать.")
        return
    
    current_progress = player.get("inc_progress", 0)
    
    if current_progress >= MAX_PROGRESS:
        await message.reply("🥚 Яйцо уже готово к вылуплению! Используй /egg чтобы увидеть питомца.")
        return
    
    new_progress = min(current_progress + INCUBATE_STEP, MAX_PROGRESS)
    
    try:
        update_player(user_id, {"inc_progress": new_progress})
        logger.info(f"Игрок {user_id} инкубировал яйцо: {current_progress}% -> {new_progress}%")
    except Exception as e:
        logger.error(f"Ошибка обновления прогресса инкубации для {user_id}: {e}")
        await message.reply("❌ Ошибка сохранения прогресса. Попробуй позже.")
        return
    
    if new_progress >= MAX_PROGRESS:
        # Яйцо вылупилось!
        try:
            update_player(user_id, {
                "hatched": True,
                "inc_progress": MAX_PROGRESS
            })
            
            pet_name = player.get("pet_name", "Питомец")
            pet_emoji = player.get("pet_emoji", "🐉")
            
            response_text = (
                f"🥚✨ *ЯЙЦО ВЫЛУПИЛОСЬ!* ✨🥚\n\n"
                f"Поздравляю! Из яйца появился {pet_emoji} **{pet_name}**!\n"
                f"Теперь ты можешь:\n"
                f"• 🍎 Кормить — /feed\n"
                f"• 💪 Тренировать — /train\n"
                f"• ⚔️ Сражаться — /battle\n"
                f"• 📊 Смотреть статистику — /stats"
            )
            
            await message.reply(response_text, parse_mode="Markdown")
            logger.info(f"Игрок {user_id}: яйцо вылупилось! Питомец {pet_name}")
            
        except Exception as e:
            logger.error(f"Ошибка при вылуплении яйца для {user_id}: {e}")
            await message.reply("❌ Ошибка при вылуплении. Попробуй ещё раз /incubate")
            return
    else:
        progress_percent = new_progress
        remaining = MAX_PROGRESS - new_progress
        steps_needed = (remaining + INCUBATE_STEP - 1) // INCUBATE_STEP
        
        progress_bar = "▓" * (new_progress // 10) + "░" * ((MAX_PROGRESS - new_progress) // 10)
        
        response_text = (
            f"🥚 *Инкубация яйца*\n\n"
            f"Прогресс: {progress_percent}%\n"
            f"{progress_bar}\n\n"
            f"Осталось нажать /incubate ещё {steps_needed} раз"
        )
        
        await message.reply(response_text, parse_mode="Markdown")

async def top_cmd(message: types.Message):
    """
    Обрабатывает команду /top — показывает таблицу лидеров арены.
    
    Аргументы:
        message (types.Message): Исходное сообщение с командой /top
    
    Возвращает:
        None: Результат отправляется в чат
    """
    
    # Константы для функции
    TOP_PLAYERS_LIMIT = 10  # Количество игроков в топе
    RATING_EMOJI = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }
    DEFAULT_EMOJI = "🏅"
    RATING_LINE = "{emoji} {username}: {wins} побед, {level} уровень"
    
    # ============================================================
    # Валидация входных данных
    # ============================================================
    
    # Проверяем, что message существует и имеет необходимые атрибуты
    if not message or not hasattr(message, 'from_user'):
        logger.error("❌ Получен пустой запрос или отсутствует from_user")
        await message.reply("❌ Произошла внутренняя ошибка. Попробуйте позже.")
        return
    
    # ============================================================
    # Проверка доступности базы данных
    # ============================================================
    
    if not supabase:
        logger.error("❌ База данных не подключена")
        await message.reply("❌ База данных недоступна. Попробуйте позже.")
        return
    
    # ============================================================
    # Получение данных из базы
    # ============================================================
    
    try:
        # Запрашиваем топ игроков по количеству побед
        response = supabase.table("players")\
            .select("user_id, pet_name, username, wins, level, losses")\
            .order("wins", desc=True)\
            .limit(TOP_PLAYERS_LIMIT)\
            .execute()
        
        players = response.data
        
        # Обработка пустого результата
        if not players:
            logger.info("❌ Таблица лидеров пуста")
            await message.reply("🏆 *Таблица лидеров* 🏆\n\nПока нет участников. Будьте первым!")
            return
        
        # Фильтрация игроков с нулевыми победами (если есть)
        players = [p for p in players if p.get('wins', 0) > 0]
        
        # Если после фильтрации список пуст
        if not players:
            await message.reply("🏆 *Таблица лидеров* 🏆\n\nПока нет участников с победами. Начните бой!")
            return
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения топа из БД: {e}")
        await message.reply("❌ Не удалось получить данные. Попробуйте позже.")
        return
    
    # ============================================================
    # Формирование ответа
    # ============================================================
    
    try:
        rating_lines = ["🏆 *ТАБЛИЦА ЛИДЕРОВ* 🏆\n", ""]
        
        for index, player in enumerate(players, start=1):
            # Обработка крайних случаев
            uid = player.get('user_id', '0')
            username = player.get('username', 'Без имени')
            wins = player.get('wins', 0)
            level = player.get('level', 1)
            
            # Безопасное получение эмодзи рейтинга
            rating_emoji = RATING_EMOJI.get(index, DEFAULT_EMOJI)
            
            # Формирование строки для каждого игрока
            line = RATING_LINE.format(
                emoji=rating_emoji,
                username=username,
                wins=wins,
                level=level
            )
            rating_lines.append(line)
        
        # Объединение в одну строку
        rating_text = "\n".join(rating_lines)
        
        # Логирование успешного выполнения
        logger.info(f"✅ Топ-{TOP_PLAYERS_LIMIT} успешно сформирован для пользователя {message.from_user.id}")
        
        # Отправка ответа
        await message.reply(rating_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"❌ Ошибка формирования ответа: {e}")
        await message.reply("❌ Произошла ошибка при формировании таблицы лидеров.")

async def battle_cmd(message: types.Message):
    """Обрабатывает команду /battle — запускает PvP-сражение между питомцами.
    
    Игрок указывает никнейм соперника (с @ или без). Если соперник не указан,
    бой происходит с случайным ботом. Результат боя определяется на основе
    характеристик питомцев с элементом случайности.
    
    Args:
        message: Объект сообщения от пользователя
        
    Returns:
        None: Результат отправляется в чат через message.reply()
    """
    MAX_HP_PERCENT = 0.3  # Максимальный процент HP для победы за один ход
    MIN_DAMAGE = 1  # Минимальный урон за ход
    XP_PER_BATTLE = 20  # Базовый опыт за бой
    XP_WIN_BONUS = 10  # Дополнительный опыт за победу
    RANDOM_FACTOR = 0.2  # Коэффициент случайности в расчёте урона
    
    user_id = str(message.from_user.id)
    
    # Получаем данные атакующего
    attacker = get_player(user_id)
    if not attacker:
        await message.reply("❌ Ты ещё не создал питомца! Используй /start")
        return
    
    # Проверяем, вылупился ли питомец
    if not attacker.get("hatched", False):
        await message.reply("🥚 Твой питомец ещё не вылупился! Используй /incubate")
        return
    
    # Проверяем, жив ли питомец
    if attacker.get("hp", 0) <= 0:
        await message.reply("💀 Твой питомец мёртв! Используй /start для возрождения")
        return
    
    # Парсим аргументы команды
    args = message.get_args().strip()
    
    # Определяем соперника
    defender = None
    defender_name = ""
    
    if args:
        # Ищем соперника по username
        defender = get_player_by_username(args)
        if not defender:
            await message.reply(f"👻 Игрок с ником {args} не найден! Убедись, что никнейм правильный.")
            return
        defender_name = f"@{defender.get('username', 'Неизвестный')}"
    else:
        # Создаём случайного бота-соперника
        bot_pet = random_pet()
        defender = {
            "user_id": 0,
            "pet_name": bot_pet["name"],
            "pet_emoji": bot_pet["emoji"],
            "hp": bot_pet["hp"],
            "max_hp": bot_pet["max_hp"],
            "strength": bot_pet["strength"],
            "agility": bot_pet["agility"],
            "magic": bot_pet["magic"],
            "defense": bot_pet["defense"],
            "speed": bot_pet["speed"],
            "level": bot_pet["level"],
            "xp": 0,
            "wins": 0,
            "losses": 0
        }
        defender_name = f"🤖 {bot_pet['emoji']} {bot_pet['name']}"
    
    # Проверяем, что соперник не сам игрок
    if str(defender.get("user_id", 0)) == user_id:
        await message.reply("🤔 Нельзя сражаться с самим собой! Найди другого соперника.")
        return
    
    # Проверяем, жив ли соперник
    if defender.get("hp", 0) <= 0:
        await message.reply(f"💀 {defender_name} уже мёртв! Выбери другого соперника.")
        return
    
    # Рассчитываем характеристики для боя
    attacker_power = (
        attacker.get("strength", 5) * 1.5 +
        attacker.get("agility", 5) * 1.2 +
        attacker.get("magic", 5) * 1.3 +
        attacker.get("speed", 5) * 1.0
    )
    
    defender_power = (
        defender.get("strength", 5) * 1.5 +
        defender.get("agility", 5) * 1.2 +
        defender.get("magic", 5) * 1.3 +
        defender.get("speed", 5) * 1.0
    )
    
    # Добавляем случайный фактор
    attacker_power *= 1 + random.uniform(-RANDOM_FACTOR, RANDOM_FACTOR)
    defender_power *= 1 + random.uniform(-RANDOM_FACTOR, RANDOM_FACTOR)
    
    # Определяем победителя
    attacker_wins = attacker_power > defender_power
    
    # Рассчитываем урон
    if attacker_wins:
        damage_percent = random.uniform(0.1, MAX_HP_PERCENT)
        damage = max(MIN_DAMAGE, int(defender.get("max_hp", 100) * damage_percent))
        defender["hp"] = max(0, defender.get("hp", 100) - damage)
    else:
        damage_percent = random.uniform(0.1, MAX_HP_PERCENT)
        damage = max(MIN_DAMAGE, int(attacker.get("max_hp", 100) * damage_percent))
        attacker["hp"] = max(0, attacker.get("hp", 100) - damage)
    
    # Формируем результат боя
    attacker_name = f"{attacker.get('pet_emoji', '🐉')} {attacker.get('pet_name', 'Питомец')}"
    
    if attacker_wins:
        # Атакующий победил
        new_wins = attacker.get("wins", 0) + 1
        new_losses = defender.get("losses", 0) + 1
        new_xp = attacker.get("xp", 0) + XP_PER_BATTLE + XP_WIN_BONUS
        
        # Обновляем данные атакующего
        update_player(user_id, {
            "hp": attacker["hp"],
            "wins": new_wins,
            "xp": new_xp
        })
        
        # Обновляем данные соперника (если это реальный игрок)
        if defender.get("user_id", 0) != 0:
            update_player(str(defender["user_id"]), {
                "hp": defender["hp"],
                "losses": new_losses
            })
        
        result_text = (
            f"⚔️ **БИТВА НА АРЕНЕ!** ⚔️\n\n"
            f"{attacker_name} VS {defender_name}\n\n"
            f"🏆 **ПОБЕДА!** {attacker_name} одержал верх!\n\n"
            f"📊 **Итоги боя:**\n"
            f"• Урон сопернику: {damage} HP\n"
            f"• Осталось HP: {attacker['hp']}/{attacker.get('max_hp', 100)}\n"
            f"• Получено опыта: +{XP_PER_BATTLE + XP_WIN_BONUS}\n"
            f"• Побед: {new_wins}"
        )
    else:
        # Атакующий проиграл
        new_losses = attacker.get("losses", 0) + 1
        new_wins = defender.get("wins", 0) + 1
        new_xp = attacker.get("xp", 0) + XP_PER_BATTLE
        
        # Обновляем данные атакующего
        update_player(user_id, {
            "hp": attacker["hp"],
            "losses": new_losses,
            "xp": new_xp
        })
        
        # Обновляем данные соперника (если это реальный игрок)
        if defender.get("user_id", 0) != 0:
            update_player(str(defender["user_id"]), {
                "hp": defender["hp"],
                "wins": new_wins
            })
        
        result_text = (
            f"⚔️ **БИТВА НА АРЕНЕ!** ⚔️\n\n"
            f"{attacker_name} VS {defender_name}\n\n"
            f"💔 **ПОРАЖЕНИЕ!** {attacker_name} проиграл бой!\n\n"
            f"📊 **Итоги боя:**\n"
            f"• Получено урона: {damage} HP\n"
            f"• Осталось HP: {attacker['hp']}/{attacker.get('max_hp', 100)}\n"
            f"• Получено опыта: +{XP_PER_BATTLE}\n"
            f"• Поражений: {new_losses}"
        )
    
    # Проверяем, не умер ли питомец
    if attacker["hp"] <= 0:
        result_text += "\n\n💀 **Твой питомец пал в бою!** Используй /start для возрождения."
    
    await message.reply(result_text)
    
    # Логируем бой
    logger.info(
        f"Бой: {attacker_name} vs {defender_name} | "
        f"Победитель: {'Атакующий' if attacker_wins else 'Соперник'} | "
        f"Урон: {damage}"
    )

async def incubate_cmd(message: types.Message):
    """
    Команда /incubate — высиживание яйца Тамагочи.
    
    Процесс высиживания:
    - Требуется наличие невысиженного яйца (hatched = False)
    - Каждое использование увеличивает прогресс на INCUBATE_STEP
    - При достижении INCUBATE_MAX_PROGRESS яйцо вылупляется, создаётся питомец
    - Если яйцо уже высижено — сообщение об ошибке
    - Если питомец уже есть — предложение использовать другие команды
    
    Константы:
        INCUBATE_STEP: шаг прогресса за одно использование (int)
        INCUBATE_MAX_PROGRESS: максимальный прогресс для вылупления (int)
        MIN_PROGRESS: минимальное значение прогресса (int)
        MAX_EGG_PROGRESS: максимальное допустимое значение прогресса (int)
    """
    # Константы
    INCUBATE_STEP = 20
    INCUBATE_MAX_PROGRESS = 100
    MIN_PROGRESS = 0
    MAX_EGG_PROGRESS = 100
    
    uid = str(message.from_user.id)
    logger.info(f"Пользователь {uid} запустил высиживание яйца")
    
    try:
        # Валидация входных данных
        if not message.from_user.id:
            logger.error(f"Некорректный ID пользователя: {message.from_user.id}")
            await message.reply("❌ Ошибка: некорректные данные пользователя")
            return
        
        # Загрузка данных игрока
        player = get_player(uid)
        logger.debug(f"Загружены данные игрока {uid}: {player}")
        
        # Проверка существования игрока
        if not player:
            logger.warning(f"Игрок {uid} не найден, создаю нового")
            player = create_player(uid)
            if not player:
                logger.error(f"Не удалось создать игрока {uid}")
                await message.reply("❌ Ошибка при создании профиля. Попробуйте позже.")
                return
            await message.reply("🌱 Новый игрок создан! Используйте /egg для получения яйца.")
            return
        
        # Проверка валидности данных игрока
        if not all(key in player for key in ['hatched', 'inc_progress', 'egg_type']):
            logger.error(f"Некорректная структура данных игрока {uid}: {player}")
            await message.reply("❌ Ошибка: повреждённые данные профиля. Обратитесь к администратору.")
            return
        
        # Проверка, что игрок ещё не вылупил питомца
        if player.get('hatched', False):
            logger.info(f"Игрок {uid} уже имеет вылупившегося питомца")
            player_data = player
            pet_name = player_data.get('pet_name', 'Питомец')
            pet_emoji = player_data.get('pet_emoji', '🐉')
            
            # Безопасное получение статистики с проверкой значений
            hp = int(player_data.get('hp', 0))
            max_hp = int(player_data.get('max_hp', 100))
            hunger = int(player_data.get('hunger', 50))
            mood = player_data.get('mood', 'спокойное')
            level = int(player_data.get('level', 1))
            xp = int(player_data.get('xp', 0))
            
            await message.reply(
                f"🌞 У тебя уже есть питомец!\n"
                f"{pet_emoji} {pet_name}\n"
                f"❤️ HP: {hp}/{max_hp}\n"
                f"🍔 Голод: {hunger}%\n"
                f"😊 Настроение: {mood}\n"
                f"⭐ Уровень: {level}, XP: {xp}\n\n"
                f"Попробуй команды:\n"
                f"/feed — покормить\n"
                f"/train — тренировать\n"
                f"/battle — сразиться\n"
                f"/stats — полная статистика"
            )
            return
        
        # Проверка наличия яйца
        if not player.get('egg_type'):
            logger.info(f"У игрока {uid} нет яйца")
            await message.reply("🥚 У тебя пока нет яйца! Используй /egg, чтобы получить его.")
            return
        
        # Валидация текущего прогресса
        current_progress = int(player.get('inc_progress', MIN_PROGRESS))
        if current_progress < MIN_PROGRESS or current_progress > MAX_EGG_PROGRESS:
            logger.warning(f"Некорректный прогресс высиживания у {uid}: {current_progress}, сбрасываю")
            current_progress = MIN_PROGRESS
        
        # Увеличение прогресса
        new_progress = current_progress + INCUBATE_STEP
        
        # Проверка на переполнение
        if new_progress > MAX_EGG_PROGRESS:
            new_progress = MAX_EGG_PROGRESS
        
        logger.info(f"Прогресс высиживания {uid}: {current_progress} -> {new_progress} ({INCUBATE_STEP}%)")
        
        # Обновление прогресса
        try:
            update_player(uid, {'inc_progress': new_progress})
            logger.debug(f"Прогресс высиживания обновлён для {uid}: {new_progress}")
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса высиживания {uid}: {e}")
            await message.reply("❌ Ошибка при сохранении прогресса. Попробуйте позже.")
            return
        
        # Проверка на вылупление
        if new_progress >= INCUBATE_MAX_PROGRESS:
            logger.info(f"Яйцо {uid} вылупилось!")
            
            # Создание питомца при вылуплении
            pet = random_pet()
            player_data = {
                "pet_name": pet["name"],
                "pet_emoji": pet["emoji"],
                "hp": pet["hp"], "max_hp": pet["max_hp"],
                "strength": pet["strength"], "agility": pet["agility"],
                "magic": pet["magic"], "defense": pet["defense"],
                "speed": pet["speed"], "hunger": pet["hunger"],
                "mood": pet["mood"], "level": pet["level"],
                "xp": pet["xp"], "wins": pet["wins"], "losses": pet["losses"],
                "egg_type": "обычное", "hatched": True,
            }
            
            try:
                update_player(uid, player_data)
                logger.info(f"Питомец создан для {uid}: {pet['name']} {pet['emoji']}")
            except Exception as e:
                logger.error(f"Ошибка создания питомца при вылуплении {uid}: {e}")
                await message.reply("❌ Ошибка при создании питомца. Попробуйте позже.")
                return
            
            # Безопасное форматирование ответа
            msg = (
                f"🎉 Яйцо <b>вылупилось!</b>\n"
                f"{pet['emoji']} <b>{pet['name']}</b>\n\n"
                f"❤️ HP: {pet['hp']}/{pet['max_hp']}\n"
                f"⚔️ Сила: {pet['strength']}\n"
                f"🏃 Скорость: {pet['speed']}\n"
                f"🛡️ Защита: {pet['defense']}\n"
                f"🍔 Голод: {pet['hunger']}%\n"
                f"😊 Настроение: {pet['mood']}\n\n"
                f"Покорми его: /feed\n"
                f"Тренируй: /train\n"
                f"Сражайся: /battle"
            )
            await message.reply(msg, parse_mode='HTML')
            
        else:
            # Яйцо ещё не вылупилось
            eggs_remaining = max(0, (INCUBATE_MAX_PROGRESS - new_progress) // INCUBATE_STEP)
            
            # Безопасное форматирование прогресс-бара
            bar_length = 10
            filled = int((new_progress / INCUBATE_MAX_PROGRESS) * bar_length)
            filled = max(0, min(filled, bar_length))  # Ограничение от 0 до bar_length
            empty = bar_length - filled
            progress_bar = '█' * filled + '░' * empty
            
            msg = (
                f"🥚 Высиживание яйца...\n"
                f"{progress_bar} {new_progress}/{INCUBATE_MAX_PROGRESS}%\n"
                f"Осталось примерно {eggs_remaining} использований\n\n"
                f"Используй /incubate, чтобы продолжить!"
            )
            await message.reply(msg)
            logger.info(f"Прогресс высиживания для {uid}: {new_progress}/{INCUBATE_MAX_PROGRESS}")
    
    except Exception as e:
        logger.error(f"Критическая ошибка в incubate_cmd для {uid}: {e}")
        await message.reply("❌ Произошла непредвиденная ошибка. Попробуйте позже.")

async def incubate_cmd(message: types.Message):
    """Инкубирует яйцо питомца, увеличивая прогресс инкубации.
    
    При достижении 100% прогресса яйцо вылупляется, и питомец становится доступен.
    Для инкубации требуется, чтобы у игрока было яйцо (hatched=False).
    
    Args:
        message: Сообщение от пользователя с командой /incubate
        
    Returns:
        None: Отправляет ответ пользователю через message.reply()
    """
    MAX_INCUBATION_PROGRESS = 100
    INCUBATION_STEP = random.randint(10, 25)
    MIN_LEVEL_FOR_INCUBATION = 1
    
    try:
        user_id = str(message.from_user.id)
        player = get_player(user_id)
        
        # Валидация: проверяем существование игрока
        if not player:
            await message.reply(
                "❌ У вас нет питомца! Используйте /start, чтобы создать его."
            )
            return
        
        # Валидация: проверяем, что у игрока есть яйцо
        if player.get("hatched", True):
            await message.reply(
                "🥚 Ваш питомец уже вылупился! Инкубация не требуется."
            )
            return
        
        # Валидация: проверяем уровень игрока
        current_level = player.get("level", MIN_LEVEL_FOR_INCUBATION)
        if current_level < MIN_LEVEL_FOR_INCUBATION:
            await message.reply(
                f"❌ Для инкубации нужен уровень {MIN_LEVEL_FOR_INCUBATION}. "
                f"Ваш уровень: {current_level}. Тренируйтесь!"
            )
            return
        
        # Получаем текущий прогресс инкубации
        current_progress = player.get("inc_progress", 0)
        
        # Проверяем, не завершена ли уже инкубация
        if current_progress >= MAX_INCUBATION_PROGRESS:
            # Вылупляем питомца
            update_player(user_id, {
                "hatched": True,
                "inc_progress": MAX_INCUBATION_PROGRESS
            })
            await message.reply(
                f"🎉 Яйцо вылупилось! Поздравляю с новым питомцем!\n"
                f"🐣 {player.get('pet_emoji', '❓')} {player.get('pet_name', 'Питомец')} появился на свет!"
            )
            logger.info(f"Игрок {user_id} вылупил питомца")
            return
        
        # Рассчитываем новый прогресс
        new_progress = min(current_progress + INCUBATION_STEP, MAX_INCUBATION_PROGRESS)
        
        # Обновляем прогресс в базе данных
        update_player(user_id, {"inc_progress": new_progress})
        
        # Формируем ответ с визуализацией прогресса
        progress_bar_length = 10
        filled_bars = int(new_progress / MAX_INCUBATION_PROGRESS * progress_bar_length)
        empty_bars = progress_bar_length - filled_bars
        progress_bar = "█" * filled_bars + "░" * empty_bars
        
        await message.reply(
            f"🥚 Инкубация яйца...\n\n"
            f"Прогресс: {new_progress}%\n"
            f"{progress_bar}\n\n"
            f"➕ Добавлено: +{INCUBATION_STEP}%\n"
            f"Осталось: {MAX_INCUBATION_PROGRESS - new_progress}%\n\n"
            f"💡 Продолжайте инкубировать, чтобы питомец вылупился!"
        )
        
        logger.info(
            f"Игрок {user_id} инкубировал яйцо: "
            f"{current_progress}% -> {new_progress}%"
        )
        
    except KeyError as e:
        logger.error(f"Ошибка доступа к данным игрока {user_id}: {e}")
        await message.reply("❌ Ошибка в данных игрока. Попробуйте позже.")
    except ValueError as e:
        logger.error(f"Ошибка преобразования данных для игрока {user_id}: {e}")
        await message.reply("❌ Ошибка обработки данных. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка инкубации для игрока {user_id}: {e}")
        await message.reply("❌ Произошла ошибка. Попробуйте позже.")

async def train_cmd(message: types.Message):
    """
    Тренировка питомца: повышает случайную характеристику.
    Каждая тренировка уменьшает сытость (-20) и увеличивает усталость (-5 HP).
    Требует: питомец высижен, сытость > 20, HP > 10.
    
    Характеристики для улучшения: сила, ловкость, магия, защита, скорость.
    Шанс на улучшение: 70% успех, 30% неудача (потрачена энергия, но без прироста).
    
    Args:
        message (types.Message): Команда /train
    
    Returns:
        None: Отправляет ответ пользователю через message.reply
    
    Raises:
        Exception: При ошибках БД или невалидном состоянии игрока
    """
    # Константы функции
    HUNGER_COST = 20
    HP_COST = 5
    SUCCESS_CHANCE = 0.70
    STAT_INCREASE_MIN = 1
    STAT_INCREASE_MAX = 3
    MIN_HUNGER_TO_TRAIN = 20
    MIN_HP_TO_TRAIN = 10
    STATS = ["strength", "agility", "magic", "defense", "speed"]
    STAT_NAMES = {
        "strength": "Сила",
        "agility": "Ловкость",
        "magic": "Магия",
        "defense": "Защита",
        "speed": "Скорость"
    }
    
    user_id = str(message.from_user.id)
    
    try:
        # Валидация: получаем игрока
        player = get_player(user_id)
        if not player:
            await message.reply("❌ Сначала создай питомца через /start!")
            logger.warning(f"Пользователь {user_id} попытался тренироваться без питомца")
            return
        
        # Проверка: питомец высижен
        if not player.get("hatched", False):
            await message.reply("🥚 Сначала высиди яйцо через /incubate!")
            return
        
        # Валидация: достаточно сытости
        if player.get("hunger", 100) < MIN_HUNGER_TO_TRAIN:
            await message.reply(f"🍽️ Слишком голоден! Нужно хотя бы {MIN_HUNGER_TO_TRAIN} сытости (сейчас {player['hunger']}). Покорми через /feed.")
            logger.info(f"Пользователь {user_id} не может тренироваться: недостаточно сытости ({player['hunger']})")
            return
        
        # Валидация: достаточно HP
        if player.get("hp", 100) <= MIN_HP_TO_TRAIN:
            await message.reply(f"💔 Слишком устал! Нужно хотя бы {MIN_HP_TO_TRAIN + 1} HP (сейчас {player['hp']}). Отдохни или съешь что-то.")
            logger.info(f"Пользователь {user_id} не может тренироваться: недостаточно HP ({player['hp']})")
            return
        
        # Выбираем случайную характеристику
        stat_to_upgrade = random.choice(STATS)
        stat_name = STAT_NAMES[stat_to_upgrade]
        
        # Определяем успех тренировки
        training_success = random.random() < SUCCESS_CHANCE
        
        # Подготовка данных для обновления
        update_data = {}
        
        # Обновляем сытость (не ниже 0)
        new_hunger = max(0, player["hunger"] - HUNGER_COST)
        update_data["hunger"] = new_hunger
        
        # Обновляем HP (не ниже 0)
        new_hp = max(0, player["hp"] - HP_COST)
        update_data["hp"] = new_hp
        
        # Результат тренировки
        stat_increase = 0
        if training_success:
            stat_increase = random.randint(STAT_INCREASE_MIN, STAT_INCREASE_MAX)
            current_stat_value = player.get(stat_to_upgrade, 0)
            update_data[stat_to_upgrade] = current_stat_value + stat_increase
            
            # Добавляем XP за успешную тренировку
            xp_gain = 5
            new_xp = player.get("xp", 0) + xp_gain
            update_data["xp"] = new_xp
            
            logger.info(f"Пользователь {user_id}: тренировка успешна. {stat_name} +{stat_increase}, XP +{xp_gain}")
        else:
            logger.info(f"Пользователь {user_id}: тренировка неудачна")
        
        # Обновляем БД
        update_player(user_id, update_data)
        
        # Формируем ответ
        pet_name = player.get("pet_name", "Питомец")
        pet_emoji = player.get("pet_emoji", "🐉")
        
        if training_success:
            response_text = (
                f"{pet_emoji} {pet_name} усердно тренируется!\n\n"
                f"✅ Тренировка успешна!\n"
                f"📈 {stat_name} повышена на {stat_increase}!\n"
                f"🌟 Получено очков опыта: 5\n"
                f"🍽️ Сытость: {new_hunger}\n"
                f"💔 HP: {new_hp}"
            )
        else:
            response_text = (
                f"{pet_emoji} {pet_name} тренируется, но...\n\n"
                f"😩 Тренировка неудачна. Характеристики не изменились.\n"
                f"🍽️ Сытость: {new_hunger}\n"
                f"💔 HP: {new_hp}\n\n"
                f"Попробуй ещё раз!"
            )
        
        await message.reply(response_text)
        logger.debug(f"Тренировка для {user_id}: {stat_to_upgrade}, успех={training_success}, сытость={new_hunger}, HP={new_hp}")
        
    except Exception as e:
        logger.error(f"Ошибка в train_cmd для {user_id}: {e}", exc_info=True)
        await message.reply("❌ Произошла ошибка. Попробуй позже или сообщи администратору.")

async def incubate_cmd(message: types.Message):
    """Инкубирует яйцо питомца, увеличивая прогресс инкубации.
    
    При достижении 100% прогресса яйцо вылупляется, и питомец становится доступен.
    Прогресс увеличивается случайным образом от 5 до 15 процентов за раз.
    
    Args:
        message: Сообщение от пользователя с командой /incubate
        
    Returns:
        None: Отправляет ответ пользователю через reply
    """
    try:
        user_id = str(message.from_user.id)
        player = get_player(user_id)
        
        if not player:
            await message.reply("❌ Сначала создай питомца через /start!")
            return
        
        # Проверка, вылупился ли уже питомец
        if player.get("hatched", False):
            await message.reply("🥚 Твой питомец уже вылупился! Используй /feed, /train или /battle.")
            return
        
        # Получаем текущий прогресс инкубации
        current_progress = player.get("inc_progress", 0)
        
        # Проверка на максимальный прогресс
        if current_progress >= 100:
            await message.reply("🥚 Яйцо уже готово к вылуплению! Используй /egg чтобы увидеть результат.")
            return
        
        # Случайное увеличение прогресса от 5 до 15 процентов
        MIN_PROGRESS_INCREMENT = 5
        MAX_PROGRESS_INCREMENT = 15
        progress_increment = random.randint(MIN_PROGRESS_INCREMENT, MAX_PROGRESS_INCREMENT)
        
        # Ограничиваем прогресс 100%
        new_progress = min(current_progress + progress_increment, 100)
        
        # Обновляем прогресс в базе данных
        update_player(user_id, {"inc_progress": new_progress})
        
        # Формируем ответ в зависимости от прогресса
        progress_bar_length = 10
        filled_bars = new_progress // progress_bar_length
        empty_bars = progress_bar_length - filled_bars
        progress_bar = "█" * filled_bars + "░" * empty_bars
        
        response_parts = [
            f"🥚 Инкубация яйца...",
            f"",
            f"Прогресс: {new_progress}%",
            f"[{progress_bar}]",
            f"",
        ]
        
        # Добавляем разные сообщения в зависимости от прогресса
        if new_progress < 25:
            response_parts.append("🐣 Яйцо только начало нагреваться...")
        elif new_progress < 50:
            response_parts.append("🐣 Слышны слабые звуки изнутри!")
        elif new_progress < 75:
            response_parts.append("🐣 Яйцо начинает трескаться!")
        elif new_progress < 100:
            response_parts.append("🐣 Ещё немного и питомец вылупится!")
        else:
            # Прогресс достиг 100% - вылупляем питомца
            update_player(user_id, {"hatched": True})
            response_parts.append("🎉 ПОЗДРАВЛЯЮ! Твой питомец вылупился!")
            response_parts.append(f"")
            response_parts.append(f"Встречай: {player.get('pet_emoji', '🐉')} {player.get('pet_name', 'Питомец')}!")
            response_parts.append(f"Теперь ты можешь кормить его (/feed), тренировать (/train) и сражаться (/battle)!")
        
        await message.reply("\n".join(response_parts))
        
        # Логируем успешную инкубацию
        logger.info(f"Игрок {user_id} инкубировал яйцо: {current_progress}% -> {new_progress}%")
        
    except KeyError as e:
        logger.error(f"Ошибка доступа к данным игрока при инкубации: {e}")
        await message.reply("❌ Произошла ошибка при обработке данных. Попробуй позже.")
    except ValueError as e:
        logger.error(f"Ошибка преобразования данных при инкубации: {e}")
        await message.reply("❌ Обнаружены некорректные данные. Обратись к администратору.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при инкубации: {e}")
        await message.reply("❌ Произошла неизвестная ошибка. Попробуй позже или сообщи администратору.")

async def inventory_cmd(message: types.Message):
    """Показывает инвентарь игрока: аптечки, зелья силы и защиты.
    
    Args:
        message: Объект сообщения от пользователя.
        
    Returns:
        None. Отправляет сообщение с инвентарём или ошибкой.
    """
    # Защита от ботов и каналов
    if message.from_user.is_bot or message.sender_chat:
        return
    
    uid = str(message.from_user.id)
    
    try:
        player = get_player(uid)
        if not player:
            await message.reply("❌ Ты ещё не создал питомца! Напиши /start")
            return
        
        # Получаем инвентарь из данных игрока
        inventory = player.get("inventory", {})
        if not inventory:
            inventory = {"medkit": 0, "strength_potion": 0, "defense_potion": 0}
            update_player(uid, {"inventory": inventory})
        
        medkits = inventory.get("medkit", 0)
        strength_potions = inventory.get("strength_potion", 0)
        defense_potions = inventory.get("defense_potion", 0)
        
        # Формируем сообщение
        text = (
            f"🎒 <b>Инвентарь</b>\n\n"
            f"🩹 Аптечки: {medkits} шт.\n"
            f"⚔️ Зелья силы: {strength_potions} шт.\n"
            f"🛡️ Зелья защиты: {defense_potions} шт.\n\n"
            f"<i>Используй /use [предмет]</i>\n"
            f"<i>Например: /use аптечка</i>"
        )
        
        await message.reply(text)
        logger.info(f"Инвентарь показан пользователю {uid}")
        
    except Exception as e:
        logger.error(f"Ошибка показа инвентаря для {uid}: {e}")
        await message.reply("❌ Произошла ошибка при загрузке инвентаря.")

async def shop_cmd(message: types.Message):
    """Показывает магазин с товарами для покупки.
    
    Args:
        message: Объект сообщения от пользователя.
        
    Returns:
        None. Отправляет сообщение с товарами магазина.
    """
    # Защита от ботов и каналов
    if message.from_user.is_bot or message.sender_chat:
        return
    
    uid = str(message.from_user.id)
    
    try:
        player = get_player(uid)
        if not player:
            await message.reply("❌ Ты ещё не создал питомца! Напиши /start")
            return
        
        coins = player.get("coins", 0)
        
        text = (
            f"🏪 <b>Магазин</b>\n\n"
            f"💰 Твои монеты: {coins}\n\n"
            f"<b>Товары:</b>\n"
            f"1️⃣ Аптечка (+50% HP) — 50 монет\n"
            f"2️⃣ Зелье силы (+30% атаки) — 100 монет\n"
            f"3️⃣ Зелье защиты (+30% защиты) — 80 монет\n\n"
            f"<i>Купить: /buy [номер]</i>\n"
            f"<i>Например: /buy 1</i>"
        )
        
        await message.reply(text)
        logger.info(f"Магазин показан пользователю {uid}")
        
    except Exception as e:
        logger.error(f"Ошибка показа магазина для {uid}: {e}")
        await message.reply("❌ Произошла ошибка при загрузке магазина.")

async def buy_cmd(message: types.Message):
    """Покупка предмета из магазина.
    
    Args:
        message: Объект сообщения от пользователя.
        
    Returns:
        None. Отправляет сообщение о результате покупки.
    """
    # Защита от ботов и каналов
    if message.from_user.is_bot or message.sender_chat:
        return
    
    uid = str(message.from_user.id)
    
    try:
        player = get_player(uid)
        if not player:
            await message.reply("❌ Ты ещё не создал питомца! Напиши /start")
            return
        
        # Парсим номер товара
        args = message.get_args().strip()
        if not args or not args.isdigit():
            await message.reply("❌ Укажи номер товара: /buy [номер]\nНапример: /buy 1")
            return
        
        item_number = int(args)
        
        # Определяем товар по номеру
        shop_items = {
            1: {"name": "аптечка", "price": 50, "key": "medkit"},
            2: {"name": "зелье силы", "price": 100, "key": "strength_potion"},
            3: {"name": "зелье защиты", "price": 80, "key": "defense_potion"}
        }
        
        if item_number not in shop_items:
            await message.reply("❌ Неверный номер товара. Доступно: 1, 2, 3")
            return
        
        item = shop_items[item_number]
        coins = player.get("coins", 0)
        
        # Проверяем достаточно ли монет
        if coins < item["price"]:
            await message.reply(
                f"❌ Недостаточно монет! Нужно: {item['price']}, у тебя: {coins}\n"
                f"Заработай монеты в бою: /battle"
            )
            return
        
        # Обновляем инвентарь и монеты
        inventory = player.get("inventory", {})
        if not inventory:
            inventory = {"medkit": 0, "strength_potion": 0, "defense_potion": 0}
        
        inventory[item["key"]] = inventory.get(item["key"], 0) + 1
        
        update_player(uid, {
            "coins": coins - item["price"],
            "inventory": inventory
        })
        
        await message.reply(
            f"✅ Куплено: {item['name']} за {item['price']} монет!\n"
            f"💰 Осталось монет: {coins - item['price']}\n"
            f"Используй /inventory чтобы увидеть свои предметы"
        )
        logger.info(f"Пользователь {uid} купил {item['name']}")
        
    except Exception as e:
        logger.error(f"Ошибка покупки для {uid}: {e}")
        await message.reply("❌ Произошла ошибка при покупке.")

async def use_cmd(message: types.Message):
    """Использование предмета из инвентаря.
    
    Args:
        message: Объект сообщения от пользователя.
        
    Returns:
        None. Отправляет сообщение о результате использования предмета.
    """
    # Защита от ботов и каналов
    if message.from_user.is_bot or message.sender_chat:
        return
    
    uid = str(message.from_user.id)
    
    try:
        player = get_player(uid)
        if not player:
            await message.reply("❌ Ты ещё не создал питомца! Напиши /start")
            return
        
        # Парсим название предмета
        args = message.get_args().strip().lower()
        if not args:
            await message.reply(
                "❌ Укажи предмет: /use [предмет]\n"
                "Доступно: аптечка, зелье силы, зелье защиты"
            )
            return
        
        inventory = player.get("inventory", {})
        if not inventory:
            inventory = {"medkit": 0, "strength_potion": 0, "defense_potion": 0}
        
        # Определяем предмет
        item_map = {
            "аптечка": {"key": "medkit", "name": "аптечка"},
            "аптечку": {"key": "medkit", "name": "аптечка"},
            "зелье силы": {"key": "strength_potion", "name": "зелье силы"},
            "зелье": {"key": "strength_potion", "name": "зелье силы"},
            "зелье защиты": {"key": "defense_potion", "name": "зелье защиты"},
            "защита": {"key": "defense_potion", "name": "зелье защиты"}
        }
        
        if args not in item_map:
            await message.reply(
                "❌ Неизвестный предмет. Доступно:\n"
                "- аптечка (восстанавливает 50% HP)\n"
                "- зелье силы (+30% к атаке на бой)\n"
                "- зелье защиты (+30% к защите на бой)"
            )
            return
        
        item = item_map[args]
        item_count = inventory.get(item["key"], 0)
        
        if item_count <= 0:
            await message.reply(f"❌ У тебя нет {item['name']}! Купи в магазине: /shop")
            return
        
        # Применяем эффект предмета
        if item["key"] == "medkit":
            # Аптечка: восстанавливает 50% от максимального HP
            max_hp = player.get("max_hp", 100)
            current_hp = player.get("hp", max_hp)
            heal_amount = int(max_hp * 0.5)
            new_hp = min(current_hp + heal_amount, max_hp)
            
            inventory[item["key"]] -= 1
            update_player(uid, {
                "hp": new_hp,
                "inventory": inventory
            })
            
            await message.reply(
                f"🩹 Использована аптечка!\n"
                f"❤️ Восстановлено {heal_amount} HP\n"
                f"Текущее HP: {new_hp}/{max_hp}"
            )
            logger.info(f"Пользователь {uid} использовал аптечку, восстановлено {heal_amount} HP")
            
        elif item["key"] == "strength_potion":
            # Зелье силы: временный бафф на атаку
            current_strength = player.get("strength", 10)
            buff_amount = int(current_strength * 0.3)
            
            inventory[item["key"]] -= 1
            update_player(uid, {
                "strength": current_strength + buff_amount,
                "inventory": inventory
            })
            
            await message.reply(
                f"⚔️ Использовано зелье силы!\n"
                f"💪 Сила увеличена на {buff_amount}\n"
                f"Текущая сила: {current_strength + buff_amount}"
            )
            logger.info(f"Пользователь {uid} использовал зелье силы, +{buff_amount} к атаке")
            
        elif item["key"] == "defense_potion":
            # Зелье защиты: временный бафф на защиту
            current_defense = player.get("defense", 10)
            buff_amount = int(current_defense * 0.3)
            
            inventory[item["key"]] -= 1
            update_player(uid, {
                "defense": current_defense + buff_amount,
                "inventory": inventory
            })
            
            await message.reply(
                f"🛡️ Использовано зелье защиты!\n"
                f"Защита увеличена на {buff_amount}\n"
                f"Текущая защита: {current_defense + buff_amount}"
            )
            logger.info(f"Пользователь {uid} использовал зелье защиты, +{buff_amount} к защите")
        
    except Exception as e:
        logger.error(f"Ошибка использования предмета для {uid}: {e}")
        await message.reply("❌ Произошла ошибка при использовании предмета.")

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