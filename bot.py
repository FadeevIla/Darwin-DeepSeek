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
    
    # Проверяем, есть ли у игрока монеты
    if p['coins'] < 10:
        await message.reply(
            "❌ <b>Недостаточно монет!</b>\n"
            "Лечение стоит 10 монет. У тебя всего {} монет.\n"
            "💰 Заработай монеты в бою (/fight) или исследуя (/explore).".format(p['coins']),
            parse_mode="HTML"
        )
        return
    
    # Проверяем, нужно ли лечение
    if p['hp'] >= p['max_hp']:
        await message.reply(
            "💚 <b>Ты полностью здоров!</b>\n"
            "У тебя {} HP из {}. Лечение не требуется.".format(p['hp'], p['max_hp']),
            parse_mode="HTML"
        )
        return
    
    # Лечим игрока
    heal_amount = min(30, p['max_hp'] - p['hp'])
    p['hp'] += heal_amount
    p['coins'] -= 10
    
    await message.reply(
        "💊 <b>Лечение завершено!</b>\n"
        "Ты восстановил {} HP.\n"
        "❤️ Текущее HP: {}/{}\n"
        "💰 Осталось монет: {}".format(heal_amount, p['hp'], p['max_hp'], p['coins']),
        parse_mode="HTML"
    )


async def explore_cmd(message: types.Message):
    """Исследование местности"""
    p = get_player(players, message.from_user.id)
    result = explore_event(p)
    await message.reply(result["message"], parse_mode="HTML")


async def rest_cmd(message: types.Message):
    """Отдых для восстановления"""
    p = get_player(players, message.from_user.id)
    result = rest(p)
    await message.reply(result["message"], parse_mode="HTML")


async def inventory_cmd(message: types.Message):
    """Просмотр инвентаря"""
    p = get_player(players, message.from_user.id)
    inventory_text = get_inventory_text(p)
    await message.reply(inventory_text, parse_mode="HTML")


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
            "❌ <b>Укажи предмет для покупки!</b>\n"
            "Пример: /buy меч\n"
            "Список товаров: /shop",
            parse_mode="HTML"
        )
        return
    
    item_name = args.strip().lower()
    result = buy_item(p, item_name)
    await message.reply(result["message"], parse_mode="HTML")


async def feedback_cmd(message: types.Message):
    """Отправка отзыва"""
    p = get_player(players, message.from_user.id)
    
    # Получаем текст отзыва из сообщения
    args = message.get_args()
    if not args:
        await message.reply(
            "❌ <b>Напиши свой отзыв!</b>\n"
            "Пример: /feedback Отличная игра!",
            parse_mode="HTML"
        )
        return
    
    feedback_text = args.strip()
    add_feedback(message.from_user.id, feedback_text)
    
    await message.reply(
        "✅ <b>Спасибо за отзыв!</b>\n"
        "Твой отзыв: \"{}\"\n"
        "Мы ценим твоё мнение!".format(feedback_text),
        parse_mode="HTML"
    )


async def clear_feedback_cmd(message: types.Message):
    """Очистка отзывов (только для администратора)"""
    # Проверяем, является ли пользователь администратором
    admin_id = os.environ.get("ADMIN_ID", "")
    if str(message.from_user.id) != admin_id:
        await message.reply(
            "❌ <b>Доступ запрещён!</b>\n"
            "Только администратор может очищать отзывы.",
            parse_mode="HTML"
        )
        return
    
    count = get_feedback_count()
    clear_feedback()
    
    await message.reply(
        "✅ <b>Отзывы очищены!</b>\n"
        "Удалено {} отзывов.".format(count),
        parse_mode="HTML"
    )


async def unknown_cmd(message: types.Message):
    """Обработка неизвестных команд"""
    await message.reply(
        "🤔 <b>Неизвестная команда!</b>\n"
        "Используй /help для списка доступных команд.",
        parse_mode="HTML"
    )


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не задан!")
        sys.exit(1)
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())
    
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