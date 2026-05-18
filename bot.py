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
        # Игрок умер
        del p["enemy"]
        await message.reply(result["message"], parse_mode="HTML")
    else:
        # Бой продолжается
        p["enemy"] = result["enemy"]
        await message.reply(result["message"], parse_mode="HTML")


async def shop_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    shop_list = get_shop_list()
    text = "🏪 <b>Магазин Уробороса</b>\n\n"
    for item in shop_list:
        text += f"• {item['name']} — {item['price']} 🪙\n"
    text += "\nИспользуй /buy <название> для покупки."
    await message.reply(text, parse_mode="HTML")


async def buy_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    args = message.get_args()
    if not args:
        await message.reply("⚠️ Укажи название предмета: /buy <название>", parse_mode="HTML")
        return
    result = buy_item(p, args)
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
    p = get_player(players, message.from_user.id)
    text = get_quest_log(p)
    await message.reply(text, parse_mode="HTML")


async def reward_cmd(message: types.Message):
    p = get_player(players, message.from_user.id)
    result = get_quest_reward(p)
    await message.reply(result, parse_mode="HTML")


async def feedback_cmd(message: types.Message):
    args = message.get_args()
    if not args:
        await message.reply("📝 Напиши отзыв: /feedback <текст>", parse_mode="HTML")
        return
    add_feedback(message.from_user.id, args)
    await message.reply("✅ Спасибо за отзыв!", parse_mode="HTML")


async def clear_feedback_cmd(message: types.Message):
    clear_feedback()
    await message.reply("🗑️ Все отзывы очищены.", parse_mode="HTML")


async def unknown_cmd(message: types.Message):
    await message.reply("❓ Неизвестная команда. Используй /help для списка команд.", parse_mode="HTML")


# ============================================================
# РЕГИСТРАЦИЯ КОМАНД
# ============================================================

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_cmd, commands=['start', 'begin', 'new'])
    dp.register_message_handler(help_cmd, commands=['help', 'h', 'commands'])
    dp.register_message_handler(stats_cmd, commands=['stats', 'stat', 'profile', 'me'])
    dp.register_message_handler(fight_cmd, commands=['fight', 'battle', 'hunt'])
    dp.register_message_handler(attack_cmd, commands=['attack', 'hit', 'strike'])
    dp.register_message_handler(shop_cmd, commands=['shop', 'store', 'market'])
    dp.register_message_handler(buy_cmd, commands=['buy', 'purchase'])
    dp.register_message_handler(inventory_cmd, commands=['inventory', 'inv', 'items', 'bag'])
    dp.register_message_handler(rest_cmd, commands=['rest', 'sleep', 'heal'])
    dp.register_message_handler(explore_cmd, commands=['explore', 'adventure', 'go'])
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