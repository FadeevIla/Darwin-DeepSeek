import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

from core.health_server import start_health_server
from core.rpg_player import get_player
from core.rpg_combat import get_random_enemy, fight_result, attack_enemy
from core.rpg_shop import get_shop_list, buy_item
from core.rpg_inventory import get_inventory_text
from core.rpg_events import rest, explore_event
from core.rpg_help import START_MESSAGE, HELP_MESSAGE
from core.feedback import add_feedback, clear_feedback, get_feedback_count

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Хранилище игроков
players = {}


# ============================================================
# КОМАНДЫ (только регистрация, логика в модулях)
# ============================================================

async def start_cmd(message: types.Message):
    get_player(players, message.from_user.id)
    await message.reply(START_MESSAGE, parse_mode="HTML")


async def help_cmd(message: types.Message):
    await message.reply(HELP_MESSAGE, parse_mode="HTML")


async def stats_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    await message.reply(
        f"📊 <b>Характеристики</b>\n"
        f"❤️ HP: {p['hp']}/{p['max_hp']}\n"
        f"⭐ Уровень: {p['level']} (XP: {p['xp']}/{p['level'] * 100})\n"
        f"🪙 Монеты: {p['coins']}\n"
        f"🌀 Проклятие: {p['curse']}/100\n"
        f"⚔️ Оружие: {p['weapon']}\n"
        f"🛡️ Броня: {p['armor']}",
        parse_mode="HTML",
    )


async def fight_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    enemy = get_random_enemy()
    result = fight_result(p, enemy)
    # Сохраняем врага если бой не окончен
    if not result["win"]:
        players[message.from_user.id]["enemy"] = result["enemy"]
    await message.reply(result["message"], parse_mode="HTML")


async def attack_cmd(message: types.Message):
    """Атака текущего врага"""
    p = get_player(players, message.from_user.id)
    
    if "enemy" not in p or p["enemy"] is None:
        await message.reply("⚠️ Нет активного врага! Используй /fight чтобы найти противника.", parse_mode="HTML")
        return
    
    result = attack_enemy(p, p["enemy"])
    
    if result["win"]:
        # Враг побеждён
        del p["enemy"]
        await message.reply(result["message"], parse_mode="HTML")
    elif result["dead"]:
        # Игрок мёртв
        del p["enemy"]
        await message.reply(result["message"], parse_mode="HTML")
    else:
        # Бой продолжается
        players[message.from_user.id]["enemy"] = result["enemy"]
        await message.reply(result["message"], parse_mode="HTML")


async def heal_cmd(message: types.Message):
    """Лечение за монеты"""
    p = get_player(players, message.from_user.id)
    
    # Проверяем, не в бою ли игрок
    if "enemy" in p and p["enemy"] is not None:
        await message.reply("⚠️ Нельзя лечиться во время боя! Сначала убей врага или сбеги.", parse_mode="HTML")
        return
    
    # Стоимость лечения зависит от уровня
    heal_cost = 10 + p["level"] * 5
    
    if p["coins"] < heal_cost:
        await message.reply(
            f"❌ Недостаточно монет! Лечение стоит {heal_cost} 🪙, у тебя только {p['coins']} 🪙.\n"
            f"Заработай монеты в бою или исследуя локации!",
            parse_mode="HTML"
        )
        return
    
    if p["hp"] >= p["max_hp"]:
        await message.reply("❤️ У тебя и так полное здоровье! Береги монеты.", parse_mode="HTML")
        return
    
    # Случайное количество восстанавливаемого HP (от 20% до 60% от max_hp)
    import random
    heal_amount = random.randint(p["max_hp"] // 5, p["max_hp"] * 3 // 5)
    
    # Если лечение превышает максимум, восстанавливаем до максимума
    if p["hp"] + heal_amount > p["max_hp"]:
        heal_amount = p["max_hp"] - p["hp"]
    
    p["coins"] -= heal_cost
    p["hp"] += heal_amount
    
    # Случайное событие при лечении
    heal_events = [
        f"🧙‍♂️ Мудрый старец исцелил тебя за {heal_cost} 🪙. Ты чувствуешь прилив сил! (+{heal_amount} ❤️)",
        f"🌿 Ты нашёл целебные травы и заварил чай. Всего за {heal_cost} 🪙 ты восстановил {heal_amount} ❤️!",
        f"🏥 В местной таверне тебя подлечили за {heal_cost} 🪙. Вкусное зелье вернуло {heal_amount} ❤️!",
        f"🔮 Таинственная незнакомка коснулась твоего лба. За {heal_cost} 🪙 ты чувствуешь себя намного лучше! (+{heal_amount} ❤️)",
        f"⚗️ Алхимик продал тебе зелье за {heal_cost} 🪙. Оно восстанавливает {heal_amount} ❤️, но оставляет странный привкус..."
    ]
    
    await message.reply(random.choice(heal_events), parse_mode="HTML")


async def explore_cmd(message: types.Message):
    """Исследование локации"""
    p = get_player(players, message.from_user.id)
    
    # Проверяем, не в бою ли игрок
    if "enemy" in p and p["enemy"] is not None:
        await message.reply("⚠️ Нельзя исследовать во время боя! Сначала разберись с врагом.", parse_mode="HTML")
        return
    
    result = explore_event(p)
    await message.reply(result["message"], parse_mode="HTML")


async def inventory_cmd(message: types.Message):
    """Просмотр инвентаря"""
    p = get_player(players, message.from_user.id)
    text = get_inventory_text(p)
    await message.reply(text, parse_mode="HTML")


async def rest_cmd(message: types.Message):
    """Отдых в лагере"""
    p = get_player(players, message.from_user.id)
    
    # Проверяем, не в бою ли игрок
    if "enemy" in p and p["enemy"] is not None:
        await message.reply("⚠️ Нельзя отдыхать во время боя! Враг не даст тебе расслабиться.", parse_mode="HTML")
        return
    
    result = rest(p)
    await message.reply(result["message"], parse_mode="HTML")


async def shop_cmd(message: types.Message):
    """Просмотр магазина"""
    p = get_player(players, message.from_user.id)
    shop_text = get_shop_list(p)
    await message.reply(shop_text, parse_mode="HTML")


async def buy_cmd(message: types.Message):
    """Покупка предмета"""
    p = get_player(players, message.from_user.id)
    
    # Получаем название предмета из сообщения
    args = message.get_args()
    if not args:
        await message.reply(
            "❌ Укажи, что хочешь купить!\n"
            "Пример: /buy меч\n"
            "Используй /shop чтобы посмотреть ассортимент.",
            parse_mode="HTML"
        )
        return
    
    result = buy_item(p, args.strip().lower())
    await message.reply(result["message"], parse_mode="HTML")


async def feedback_cmd(message: types.Message):
    """Отправка отзыва"""
    args = message.get_args()
    if not args:
        await message.reply(
            "❌ Напиши свой отзыв после команды!\n"
            "Пример: /feedback Отличная игра!",
            parse_mode="HTML"
        )
        return
    
    add_feedback(message.from_user.id, args)
    await message.reply("✅ Спасибо за отзыв! Мы учтём твои пожелания.", parse_mode="HTML")


async def clear_feedback_cmd(message: types.Message):
    """Очистка отзывов (только для админа)"""
    # Проверяем, является ли пользователь админом
    if message.from_user.id != 123456789:  # Замени на свой ID
        await message.reply("❌ Только администратор может очищать отзывы!", parse_mode="HTML")
        return
    
    count = get_feedback_count()
    clear_feedback()
    await message.reply(f"✅ Очищено {count} отзывов.", parse_mode="HTML")


async def unknown_cmd(message: types.Message):
    """Обработка неизвестных команд"""
    await message.reply(
        "❓ Неизвестная команда. Используй /help чтобы узнать доступные команды.",
        parse_mode="HTML"
    )


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не задан!")
        sys.exit(1)
    
    bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    
    # Регистрация команд
    dp.register_message_handler(start_cmd, commands=['start'])
    dp.register_message_handler(help_cmd, commands=['help'])
    dp.register_message_handler(stats_cmd, commands=['stats'])
    dp.register_message_handler(fight_cmd, commands=['fight'])
    dp.register_message_handler(attack_cmd, commands=['attack'])
    dp.register_message_handler(heal_cmd, commands=['heal'])
    dp.register_message_handler(explore_cmd, commands=['explore'])
    dp.register_message_handler(inventory_cmd, commands=['inventory'])
    dp.register_message_handler(rest_cmd, commands=['rest'])
    dp.register_message_handler(shop_cmd, commands=['shop'])
    dp.register_message_handler(buy_cmd, commands=['buy'])
    dp.register_message_handler(feedback_cmd, commands=['feedback'])
    dp.register_message_handler(clear_feedback_cmd, commands=['clear_feedback'])
    dp.register_message_handler(unknown_cmd)
    
    # Запуск health сервера (если нужно)
    try:
        start_health_server()
    except Exception as e:
        logger.warning(f"Health server не запущен: {e}")
    
    logger.info("🐉 Уроборос запущен!")
    executor.start_polling(dp)