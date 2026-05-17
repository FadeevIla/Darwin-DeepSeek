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
from core.rpg_combat import get_random_enemy, fight_result
from core.rpg_shop import get_shop_list, buy_item
from core.rpg_inventory import get_inventory_text
from core.rpg_events import rest
from core.rpg_help import START_MESSAGE, HELP_MESSAGE

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


async def inventory_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    await message.reply(get_inventory_text(p), parse_mode="HTML")


async def rest_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    msg = rest(p)
    await message.reply(msg, parse_mode="HTML")


async def shop_cmd(message: types.Message):
    await message.reply(
        f"🛒 <b>Торговец</b>\n\n{get_shop_list()}\n\n"
        f"Напиши /buy [номер] для покупки.",
        parse_mode="HTML",
    )


async def buy_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    try:
        idx = int(message.get_args().strip()) - 1
        success, msg = buy_item(p, idx)
    except (ValueError, IndexError):
        success, msg = False, "Укажи номер товара: /buy 1"
    await message.reply(msg)


async def feedback_cmd(message: types.Message):
    """Команда для отправки отзыва"""
    from core.feedback import add_feedback
    
    text = message.get_args().strip()
    if not text:
        await message.reply("✏️ Напиши отзыв после команды, например:\n/feedback Отличная игра!")
        return
    
    success, msg = add_feedback(message.from_user.id, text)
    await message.reply(msg)


async def clear_feedback_cmd(message: types.Message):
    """Команда для очистки отзывов игрока"""
    from core.feedback import clear_player_feedback
    
    success, msg = clear_player_feedback(message.from_user.id)
    await message.reply(msg)


async def attack_cmd(message: types.Message):
    """Команда атаки в бою"""
    from core.rpg_combat import attack_enemy
    
    p = get_player(players, message.from_user.id)
    if "enemy" not in p:
        await message.reply("⚔️ Сначала начни бой: /fight", parse_mode="HTML")
        return
    
    enemy = p["enemy"]
    result = attack_enemy(p, enemy)
    
    # Обновляем состояние врага
    if result.get("enemy"):
        p["enemy"] = result["enemy"]
    else:
        p.pop("enemy", None)
    
    await message.reply(result["message"], parse_mode="HTML")


async def heal_cmd(message: types.Message):
    """Команда лечения в бою"""
    from core.rpg_combat import heal_in_combat
    
    p = get_player(players, message.from_user.id)
    if "enemy" not in p:
        await message.reply("🛌 Сейчас ты не в бою. Используй /rest для отдыха.", parse_mode="HTML")
        return
    
    enemy = p["enemy"]
    # Союзники не атакуют, просто лечимся
    result = heal_in_combat(p, enemy)
    
    if result.get("enemy"):
        p["enemy"] = result["enemy"]
    else:
        p.pop("enemy", None)
    
    await message.reply(result["message"], parse_mode="HTML")


async def explore_cmd(message: types.Message):
    """Команда исследования локации"""
    from core.rpg_events import explore_location
    
    p = get_player(players, message.from_user.id)
    
    # Проверяем можно ли исследовать
    if p["hp"] <= 0:
        await message.reply("💀 Ты слишком слаб для исследований! Используй /rest.", parse_mode="HTML")
        return
    
    result = explore_location(p)
    await message.reply(result, parse_mode="HTML")


if __name__ == "__main__":
    start_health_server()
    
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())

    dp.register_message_handler(start_cmd, commands=['start'])
    dp.register_message_handler(help_cmd, commands=['help'])
    dp.register_message_handler(stats_cmd, commands=['stats'])
    dp.register_message_handler(fight_cmd, commands=['fight'])
    dp.register_message_handler(inventory_cmd, commands=['inventory'])
    dp.register_message_handler(rest_cmd, commands=['rest'])
    dp.register_message_handler(shop_cmd, commands=['shop'])
    dp.register_message_handler(buy_cmd, commands=['buy'])
    dp.register_message_handler(feedback_cmd, commands=['feedback'])
    dp.register_message_handler(clear_feedback_cmd, commands=['clear_feedback'])
    dp.register_message_handler(attack_cmd, commands=['attack'])
    dp.register_message_handler(heal_cmd, commands=['heal'])
    dp.register_message_handler(explore_cmd, commands=['explore'])

    logger.info("🐉 Уроборос запущен!")
    executor.start_polling(dp)