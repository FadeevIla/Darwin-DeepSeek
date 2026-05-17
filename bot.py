import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

from core.health_server import start_health_server
from core.feedback import add_feedback, clear_feedback
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


async def report_cmd(message: types.Message):
    """Команда для отправки отзыва/багрепорта"""
    args = message.get_args().strip()
    if not args:
        await message.reply(
            "📝 <b>Отправка отзыва</b>\n\n"
            "Напиши /report [текст отзыва] — и мы его получим.\n"
            "Спасибо за помощь в улучшении игры!",
            parse_mode="HTML"
        )
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or "Неизвестный"
    
    # Сохраняем отзыв
    add_feedback(user_id, username, args)
    
    # Случайный ответ
    import random
    responses = [
        "✅ Спасибо за отзыв! Мы обязательно его рассмотрим.",
        "👍 Отлично! Твой отзыв поможет сделать игру лучше.",
        "📨 Получено! Команда разработки благодарит тебя.",
        "🌟 Твой голос важен для нас! Спасибо за обратную связь."
    ]
    
    await message.reply(
        f"{random.choice(responses)}\n\n"
        f"<i>Твой отзыв:</i> {args}",
        parse_mode="HTML"
    )
    
    logger.info(f"Отзыв от {username} (ID: {user_id}): {args}")


async def feedback_cmd(message: types.Message):
    """Команда для просмотра статистики отзывов (только для админа)"""
    # Простая проверка — только для определённых пользователей
    admin_ids = [123456789]  # Замени на реальные ID администраторов
    
    if message.from_user.id not in admin_ids:
        await message.reply("❌ У тебя нет доступа к этой команде.")
        return
    
    from core.feedback import get_feedback_stats
    stats = get_feedback_stats()
    
    await message.reply(
        f"📊 <b>Статистика отзывов</b>\n\n"
        f"Всего отзывов: {stats['total']}\n"
        f"Последний отзыв: {stats['last_feedback'] or 'нет'}",
        parse_mode="HTML"
    )


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
    dp.register_message_handler(help_cmd, commands=['help'])
    dp.register_message_handler(stats_cmd, commands=['stats'])
    dp.register_message_handler(fight_cmd, commands=['fight'])
    dp.register_message_handler(inventory_cmd, commands=['inventory'])
    dp.register_message_handler(rest_cmd, commands=['rest'])
    dp.register_message_handler(shop_cmd, commands=['shop'])
    dp.register_message_handler(buy_cmd, commands=['buy'])
    dp.register_message_handler(report_cmd, commands=['report'])
    dp.register_message_handler(feedback_cmd, commands=['feedback'])

    logger.info("🐉 Уроборос запущен!")
    executor.start_polling(dp)