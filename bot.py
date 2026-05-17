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
            "💰 Лечение стоит 10 монет.\n"
            "💪 Заработай монеты в бою или на исследовании!",
            parse_mode="HTML"
        )
        return
    
    # Проверяем, нужно ли лечение
    if p['hp'] >= p['max_hp']:
        await message.reply(
            "💚 <b>Ты полностью здоров!</b>\n"
            "Нет необходимости лечиться.",
            parse_mode="HTML"
        )
        return
    
    # Случайное количество восстанавливаемого HP (20-50)
    import random
    heal_amount = random.randint(20, 50)
    
    # Ограничиваем максимальным HP
    old_hp = p['hp']
    p['hp'] = min(p['hp'] + heal_amount, p['max_hp'])
    actual_heal = p['hp'] - old_hp
    p['coins'] -= 10
    
    # Случайные события при лечении
    heal_events = [
        f"🧙‍♂️ <b>Мудрый целитель</b> восстанавливает тебе {actual_heal} HP за 10 монет!",
        f"🌿 <b>Травяной отвар</b> возвращает {actual_heal} HP. Цена - 10 монет.",
        f"✨ <b>Магическое восстановление</b> даёт {actual_heal} HP. Потрачено 10 монет.",
        f"🕯️ <b>Ритуал исцеления</b> восстанавливает {actual_heal} HP. С тебя 10 монет.",
        f"💫 <b>Светлая энергия</b> наполняет тебя, возвращая {actual_heal} HP. -10 монет."
    ]
    
    await message.reply(
        f"{random.choice(heal_events)}\n\n"
        f"❤️ HP: {p['hp']}/{p['max_hp']}\n"
        f"🪙 Монеты: {p['coins']}",
        parse_mode="HTML"
    )


async def explore_cmd(message: types.Message):
    """Исследование местности"""
    p = get_player(players, message.from_user.id)
    result = explore_event(p)
    await message.reply(result, parse_mode="HTML")


async def inventory_cmd(message: types.Message):
    """Просмотр инвентаря"""
    p = get_player(players, message.from_user.id)
    inv_text = get_inventory_text(p)
    await message.reply(inv_text, parse_mode="HTML")


async def rest_cmd(message: types.Message):
    """Отдых в таверне"""
    p = get_player(players, message.from_user.id)
    result = rest(p)
    await message.reply(result, parse_mode="HTML")


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
            "Используй /shop для просмотра доступных предметов.",
            parse_mode="HTML"
        )
        return
    
    item_name = args.strip().lower()
    result = buy_item(p, item_name)
    await message.reply(result, parse_mode="HTML")


async def feedback_cmd(message: types.Message):
    """Отправка отзыва"""
    args = message.get_args()
    if not args:
        await message.reply(
            "📝 <b>Напиши свой отзыв после команды!</b>\n"
            "Пример: /feedback Отличная игра!",
            parse_mode="HTML"
        )
        return
    
    feedback_text = args.strip()
    add_feedback(message.from_user.id, feedback_text)
    
    # Случайные ответы на отзывы
    import random
    responses = [
        "🌟 Спасибо за твой отзыв! Он поможет сделать игру лучше!",
        "💫 Твоё мнение очень важно для нас! Спасибо!",
        "✨ Отзыв принят! Мы ценим твоё участие в развитии игры!",
        "🎯 Благодарим за обратную связь! Каждый отзыв делает Уроборос лучше!",
        "📖 Твой отзыв записан в летопись Уробороса! Спасибо!"
    ]
    
    await message.reply(
        f"{random.choice(responses)}\n\n"
        f"<i>Твой отзыв:</i> {feedback_text}",
        parse_mode="HTML"
    )


async def clear_feedback_cmd(message: types.Message):
    """Очистка отзывов"""
    count = get_feedback_count()
    if count == 0:
        await message.reply(
            "📭 <b>Нет отзывов для очистки.</b>",
            parse_mode="HTML"
        )
        return
    
    clear_feedback()
    await message.reply(
        f"🧹 <b>Очищено {count} отзывов!</b>\n"
        f"Теперь можно собирать новые.",
        parse_mode="HTML"
    )


async def unknown_cmd(message: types.Message):
    """Обработка неизвестных команд"""
    import random
    
    responses = [
        "🤔 <b>Неизвестная команда.</b>\nИспользуй /help для списка команд.",
        "❓ <b>Я не знаю такой команды.</b>\nПопробуй /help.",
        "😕 <b>Что-то пошло не так.</b>\nВведи /help чтобы узнать доступные команды.",
        "🧙‍♂️ <b>Старый маг качает головой:</b>\n'Я не знаю такого заклинания. Попробуй /help.'",
        "📜 <b>В древних свитках нет такой команды.</b>\nИспользуй /help для изучения доступных заклинаний."
    ]
    
    await message.reply(random.choice(responses), parse_mode="HTML")


# ============================================================
# ЗАПУСК БОТА
# ============================================================

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
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