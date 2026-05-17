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
from core.rpg_combat import get_random_enemy, attack_turn
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
    result = attack_turn(p, enemy)
    # Сохраняем врага если бой не окончен
    if not result.get("win") and not result.get("dead"):
        players[message.from_user.id]["enemy"] = result["enemy"]
    await message.reply(result["message"], parse_mode="HTML")


async def attack_cmd(message: types.Message):
    """Атака текущего врага"""
    p = get_player(players, message.from_user.id)
    
    if "enemy" not in p or p["enemy"] is None:
        await message.reply("⚠️ Нет активного врага! Используй /fight чтобы найти противника.", parse_mode="HTML")
        return
    
    result = attack_turn(p, p["enemy"])
    
    if result.get("win"):
        # Враг побеждён
        del p["enemy"]
        await message.reply(result["message"], parse_mode="HTML")
    elif result.get("dead"):
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
    
    if p['hp'] >= p['max_hp']:
        await message.reply("❤️ У тебя уже полное здоровье!", parse_mode="HTML")
        return
    
    if p['coins'] < 10:
        await message.reply("💰 Недостаточно монет! Лечение стоит 10 монет.", parse_mode="HTML")
        return
    
    heal_amount = min(30, p['max_hp'] - p['hp'])
    p['hp'] += heal_amount
    p['coins'] -= 10
    
    await message.reply(
        f"💚 Ты выпил лечебное зелье и восстановил {heal_amount} HP!\n"
        f"❤️ Текущее HP: {p['hp']}/{p['max_hp']}\n"
        f"🪙 Осталось монет: {p['coins']}",
        parse_mode="HTML"
    )


async def shop_cmd(message: types.Message):
    """Магазин"""
    p = get_player(players, message.from_user.id)
    shop_text = get_shop_list(p)
    await message.reply(shop_text, parse_mode="HTML")


async def buy_cmd(message: types.Message):
    """Покупка предмета"""
    p = get_player(players, message.from_user.id)
    
    args = message.get_args()
    if not args:
        await message.reply("📝 Используй: /buy <название предмета>\nНапример: /buy Меч", parse_mode="HTML")
        return
    
    result = buy_item(p, args)
    await message.reply(result, parse_mode="HTML")


async def inventory_cmd(message: types.Message):
    """Инвентарь"""
    p = get_player(players, message.from_user.id)
    inv_text = get_inventory_text(p)
    await message.reply(inv_text, parse_mode="HTML")


async def rest_cmd(message: types.Message):
    """Отдых"""
    p = get_player(players, message.from_user.id)
    result = rest(p)
    await message.reply(result, parse_mode="HTML")


async def explore_cmd(message: types.Message):
    """Исследование"""
    p = get_player(players, message.from_user.id)
    result = explore_event(p)
    await message.reply(result, parse_mode="HTML")


async def feedback_cmd(message: types.Message):
    """Оставить отзыв"""
    args = message.get_args()
    if not args:
        await message.reply("📝 Используй: /feedback <текст отзыва>", parse_mode="HTML")
        return
    
    add_feedback(message.from_user.id, args)
    count = get_feedback_count()
    await message.reply(f"✅ Спасибо за отзыв! Всего отзывов: {count}", parse_mode="HTML")


async def clear_feedback_cmd(message: types.Message):
    """Очистить отзывы"""
    clear_feedback()
    await message.reply("🗑️ Все отзывы очищены!", parse_mode="HTML")


async def unknown_cmd(message: types.Message):
    """Неизвестная команда"""
    await message.reply(
        "❓ Неизвестная команда. Используй /help для списка команд.",
        parse_mode="HTML"
    )


# ============================================================
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ============================================================

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_cmd, commands=['start'])
    dp.register_message_handler(help_cmd, commands=['help'])
    dp.register_message_handler(stats_cmd, commands=['stats'])
    dp.register_message_handler(fight_cmd, commands=['fight'])
    dp.register_message_handler(attack_cmd, commands=['attack'])
    dp.register_message_handler(heal_cmd, commands=['heal'])
    dp.register_message_handler(shop_cmd, commands=['shop'])
    dp.register_message_handler(buy_cmd, commands=['buy'])
    dp.register_message_handler(inventory_cmd, commands=['inventory'])
    dp.register_message_handler(rest_cmd, commands=['rest'])
    dp.register_message_handler(explore_cmd, commands=['explore'])
    dp.register_message_handler(feedback_cmd, commands=['feedback'])
    dp.register_message_handler(clear_feedback_cmd, commands=['clear_feedback'])
    dp.register_message_handler(unknown_cmd)


# ============================================================
# ЗАПУСК БОТА
# ============================================================

if __name__ == '__main__':
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не установлен!")
        sys.exit(1)
    
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    
    # Регистрация команд
    register_handlers(dp)
    
    # Запуск health сервера
    try:
        start_health_server()
    except Exception as e:
        logger.warning(f"Health server не запущен: {e}")
    
    logger.info("🐉 Уроборос запущен!")
    executor.start_polling(dp)