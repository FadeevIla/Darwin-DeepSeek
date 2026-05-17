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
    
    args = message.get_args().strip()
    if not args:
        await message.reply(
            "📝 <b>Отзыв</b>\n\n"
            "Напиши /feedback [твой отзыв] чтобы оставить отзыв.\n"
            "Например: /feedback Отличная игра!",
            parse_mode="HTML"
        )
        return
    
    success, msg = add_feedback(message.from_user.id, args)
    await message.reply(msg, parse_mode="HTML")


async def clear_feedback_cmd(message: types.Message):
    """Команда для очистки отзывов"""
    from core.feedback import clear_feedback
    
    success, msg = clear_feedback()
    await message.reply(msg, parse_mode="HTML")


async def attack_cmd(message: types.Message):
    """Команда для атаки врага в бою"""
    p = get_player(players, message.from_user.id)
    
    if "enemy" not in p or p["enemy"] is None:
        await message.reply(
            "⚔️ <b>Нет врага!</b>\n\n"
            "Сначала найди врага командой /fight",
            parse_mode="HTML"
        )
        return
    
    enemy = p["enemy"]
    result = fight_result(p, enemy)
    
    if result["win"]:
        # Враг побеждён
        del p["enemy"]
        await message.reply(
            f"🎉 <b>Победа!</b>\n\n{result['message']}",
            parse_mode="HTML"
        )
    else:
        # Бой продолжается
        if p["hp"] <= 0:
            # Игрок умер
            del p["enemy"]
            await message.reply(
                f"💀 <b>Ты погиб!</b>\n\n{result['message']}",
                parse_mode="HTML"
            )
        else:
            # Обновляем врага
            p["enemy"] = result["enemy"]
            await message.reply(
                f"⚔️ <b>Бой продолжается!</b>\n\n{result['message']}",
                parse_mode="HTML"
            )


async def heal_cmd(message: types.Message):
    """Команда для лечения"""
    p = get_player(players, message.from_user.id)
    
    # Проверяем, есть ли зелья
    if "potions" not in p:
        p["potions"] = 0
    
    if p["potions"] <= 0:
        await message.reply(
            "🧪 <b>Нет зелий!</b>\n\n"
            "Купи зелья в магазине /shop",
            parse_mode="HTML"
        )
        return
    
    # Лечимся
    heal_amount = 30 + p["level"] * 5
    old_hp = p["hp"]
    p["hp"] = min(p["max_hp"], p["hp"] + heal_amount)
    p["potions"] -= 1
    
    actual_heal = p["hp"] - old_hp
    
    await message.reply(
        f"🧪 <b>Использовано зелье!</b>\n\n"
        f"❤️ Восстановлено HP: +{actual_heal}\n"
        f"❤️ Текущее HP: {p['hp']}/{p['max_hp']}\n"
        f"🧪 Осталось зелий: {p['potions']}",
        parse_mode="HTML"
    )


async def explore_cmd(message: types.Message):
    """Команда для исследования"""
    import random
    
    p = get_player(players, message.from_user.id)
    
    # Случайное событие
    events = [
        {
            "name": "Находка",
            "message": "Ты нашёл старый сундук!",
            "effect": lambda p: p.update({"coins": p["coins"] + random.randint(5, 20)}),
            "result": lambda: f"🪙 +{random.randint(5, 20)} монет"
        },
        {
            "name": "Ловушка",
            "message": "Ты попал в ловушку!",
            "effect": lambda p: p.update({"hp": max(0, p["hp"] - random.randint(5, 15))}),
            "result": lambda: f"💔 -{random.randint(5, 15)} HP"
        },
        {
            "name": "Зелье",
            "message": "Ты нашёл зелье здоровья!",
            "effect": lambda p: p.update({"potions": p.get("potions", 0) + 1}),
            "result": lambda: "🧪 +1 зелье"
        },
        {
            "name": "Опыт",
            "message": "Ты нашёл древний свиток знаний!",
            "effect": lambda p: p.update({"xp": p["xp"] + random.randint(10, 30)}),
            "result": lambda: f"⭐ +{random.randint(10, 30)} XP"
        },
        {
            "name": "Проклятие",
            "message": "Ты коснулся проклятого артефакта!",
            "effect": lambda p: p.update({"curse": min(100, p["curse"] + random.randint(5, 15))}),
            "result": lambda: f"🌀 +{random.randint(5, 15)} проклятия"
        },
        {
            "name": "Удача",
            "message": "Ты нашёл мешочек с монетами!",
            "effect": lambda p: p.update({"coins": p["coins"] + random.randint(10, 30)}),
            "result": lambda: f"🪙 +{random.randint(10, 30)} монет"
        }
    ]
    
    event = random.choice(events)
    event["effect"](p)
    
    await message.reply(
        f"🔍 <b>Исследование</b>\n\n"
        f"{event['message']}\n"
        f"{event['result']()}\n\n"
        f"❤️ HP: {p['hp']}/{p['max_hp']}\n"
        f"🪙 Монеты: {p['coins']}\n"
        f"⭐ XP: {p['xp']}",
        parse_mode="HTML"
    )


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
    dp.register_message_handler(feedback_cmd, commands=['feedback'])
    dp.register_message_handler(clear_feedback_cmd, commands=['clear_feedback'])
    dp.register_message_handler(attack_cmd, commands=['attack'])
    dp.register_message_handler(heal_cmd, commands=['heal'])
    dp.register_message_handler(explore_cmd, commands=['explore'])

    logger.info("🐉 Уроборос запущен!")
    executor.start_polling(dp)