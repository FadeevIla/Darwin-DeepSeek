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
from core.rpg_quests import get_quest_log, complete_quest_step, get_quest_reward

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
        enemy_name = p["enemy"]["name"]
        del p["enemy"]
        # Проверяем квесты на убийство врага
        quest_message = complete_quest_step(p, f"kill_{enemy_name}")
        full_message = result["message"]
        if quest_message:
            full_message += "\n\n" + quest_message
        await message.reply(full_message, parse_mode="HTML")
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
    
    # Стоимость лечения зависит от уровня
    heal_cost = 10 + (p["level"] * 5)
    
    if p["coins"] < heal_cost:
        await message.reply(f"❌ Недостаточно монет! Лечение стоит {heal_cost} 🪙.", parse_mode="HTML")
        return
    
    if p["hp"] >= p["max_hp"]:
        await message.reply("❤️ У тебя уже полное здоровье!", parse_mode="HTML")
        return
    
    # Лечим на 30% от максимального HP
    heal_amount = int(p["max_hp"] * 0.3)
    p["hp"] = min(p["hp"] + heal_amount, p["max_hp"])
    p["coins"] -= heal_cost
    
    await message.reply(
        f"💚 Ты восстановил {heal_amount} HP!\n"
        f"❤️ {p['hp']}/{p['max_hp']}\n"
        f"🪙 Потрачено: {heal_cost} монет",
        parse_mode="HTML",
    )


async def shop_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    items = get_shop_list(p)
    text = "🏪 <b>Магазин:</b>\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. {item['name']} — {item['price']} 🪙\n"
        text += f"   {item.get('desc', '')}\n"
    text += "\n<i>Купить: /buy номер_товара</i>"
    await message.reply(text, parse_mode="HTML")


async def buy_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    try:
        item_num = int(message.get_args()) - 1
    except (ValueError, TypeError):
        await message.reply("❌ Укажи номер товара из списка /shop", parse_mode="HTML")
        return
    
    result = buy_item(p, item_num)
    await message.reply(result, parse_mode="HTML")


async def inventory_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    text = get_inventory_text(p)
    await message.reply(text, parse_mode="HTML")


async def rest_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    result = rest(p)
    await message.reply(result, parse_mode="HTML")


async def explore_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    result = explore_event(p)
    await message.reply(result, parse_mode="HTML")


async def quests_cmd(message: types.Message):
    """Просмотр активных квестов"""
    p = get_player(players, message.from_user.id)
    quest_log = get_quest_log(p)
    await message.reply(quest_log, parse_mode="HTML")


async def reward_cmd(message: types.Message):
    """Получить награду за выполненный квест"""
    p = get_player(players, message.from_user.id)
    result = get_quest_reward(p)
    await message.reply(result, parse_mode="HTML")


async def feedback_cmd(message: types.Message):
    """Оставить отзыв"""
    parts = message.get_args().split()
    if not parts:
        await message.reply("❌ Укажи отзыв после команды: /feedback отличная игра!", parse_mode="HTML")
        return
    user_id = message.from_user.id
    add_feedback(user_id, message.get_args())
    await message.reply("✅ Спасибо за отзыв!", parse_mode="HTML")


async def clear_feedback_cmd(message: types.Message):
    """Очистить отзывы (только для админа)"""
    ADMIN_ID = 123456789  # Заменить на реальный ID админа
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Только администратор может очищать отзывы!", parse_mode="HTML")
        return
    clear_feedback()
    await message.reply("✅ Отзывы очищены!", parse_mode="HTML")


async def unknown_cmd(message: types.Message):
    await message.reply("❓ Неизвестная команда. Используй /help", parse_mode="HTML")


# ============================================================
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ
# ============================================================

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_cmd, commands=['start'])
    dp.register_message_handler(help_cmd, commands=['help'])
    dp.register_message_handler(stats_cmd, commands=['stats', 'profile'])
    dp.register_message_handler(fight_cmd, commands=['fight', 'search'])
    dp.register_message_handler(attack_cmd, commands=['attack', 'hit'])
    dp.register_message_handler(heal_cmd, commands=['heal', 'health'])
    dp.register_message_handler(shop_cmd, commands=['shop', 'market'])
    dp.register_message_handler(buy_cmd, commands=['buy', 'purchase'])
    dp.register_message_handler(inventory_cmd, commands=['inventory', 'bag', 'items'])
    dp.register_message_handler(rest_cmd, commands=['rest', 'sleep'])
    dp.register_message_handler(explore_cmd, commands=['explore', 'adventure'])
    dp.register_message_handler(quests_cmd, commands=['quests', 'missions', 'tasks'])
    dp.register_message_handler(reward_cmd, commands=['reward', 'claim', 'complete'])
    dp.register_message_handler(feedback_cmd, commands=['feedback', 'review'])
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