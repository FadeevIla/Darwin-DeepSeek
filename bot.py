from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from core import environ_map
from datetime import datetime, timedelta
import secrets
import asyncio
import random
import logging

logger = logging.getLogger(__name__)
BOT_TOKEN = environ_map['TELEGRAM_BOT_TOKEN']

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# RPG система боя с характеристиками
class RPGCharacter:
    def __init__(self, user_id):
        self.user_id = user_id
        self.strength = random.randint(5, 15)
        self.agility = random.randint(5, 15)
        self.magic = random.randint(5, 15)
        self.curse = random.randint(0, 5)
        self.hp = 100
        self.max_hp = 100

    def attack_physical(self):
        damage = self.strength + random.randint(0, 5)
        if self.curse > 0:
            damage -= self.curse // 2
        return max(1, damage)

    def attack_magical(self):
        damage = self.magic + random.randint(0, 10)
        if self.curse > 0:
            damage -= self.curse
        return max(1, damage)

    def defend(self, damage):
        reduction = self.agility // 3
        actual_damage = max(1, damage - reduction)
        self.hp -= actual_damage
        return actual_damage

    def is_alive(self):
        return self.hp > 0

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def curse_effect(self):
        if self.curse > 0:
            self.hp -= self.curse
            return self.curse
        return 0

characters = {}

async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        characters[user_id] = RPGCharacter(user_id)
        await message.reply("Добро пожаловать в Уроборос! Твой персонаж создан.\n"
                           f"Сила: {characters[user_id].strength}\n"
                           f"Ловкость: {characters[user_id].agility}\n"
                           f"Магия: {characters[user_id].magic}\n"
                           f"Проклятие: {characters[user_id].curse}")
    else:
        await message.reply("Ты уже в игре! Используй /help для списка команд.")

async def help_command(message: types.Message):
    await message.reply("Доступные команды:\n"
                       "/start - Начать игру\n"
                       "/help - Помощь\n"
                       "/echo <текст> - Повторить текст\n"
                       "/dice - Бросить кубик\n"
                       "/coinflip - Подбросить монетку\n"
                       "/battle - Сразиться с монстром")

async def echo(message: types.Message):
    text = message.get_args()
    if text:
        await message.reply(text)
    else:
        await message.reply("Напиши текст после команды /echo")

async def dice(message: types.Message):
    result = random.randint(1, 6)
    await message.reply(f"🎲 Выпало: {result}")

async def coinflip(message: types.Message):
    result = random.choice(['Орёл', 'Решка'])
    await message.reply(f"🪙 {result}")

async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return

    player = characters[user_id]
    monster = RPGCharacter(0)
    monster.strength = random.randint(3, 10)
    monster.agility = random.randint(3, 10)
    monster.magic = random.randint(3, 10)
    monster.hp = 50 + random.randint(0, 30)

    battle_log = [f"⚔️ Бой начинается! Твои характеристики:",
                  f"Сила: {player.strength}, Ловкость: {player.agility}, Магия: {player.magic}",
                  f"Монстр: Сила: {monster.strength}, Ловкость: {monster.agility}, Магия: {monster.magic}",
                  ""]

    turn = 1
    while player.is_alive() and monster.is_alive():
        battle_log.append(f"--- Ход {turn} ---")

        # Ход игрока
        action = random.choice(['physical', 'magical'])
        if action == 'physical':
            damage = player.attack_physical()
            actual_damage = monster.defend(damage)
            battle_log.append(f"Ты атакуешь физически: {actual_damage} урона монстру")
        else:
            damage = player.attack_magical()
            actual_damage = monster.defend(damage)
            battle_log.append(f"Ты атакуешь магией: {actual_damage} урона монстру")

        if not monster.is_alive():
            battle_log.append("🎉 Ты победил монстра!")
            break

        # Ход монстра
        monster_action = random.choice(['physical', 'magical'])
        if monster_action == 'physical':
            damage = monster.attack_physical()
            actual_damage = player.defend(damage)
            battle_log.append(f"Монстр атакует физически: {actual_damage} урона тебе")
        else:
            damage = monster.attack_magical()
            actual_damage = player.defend(damage)
            battle_log.append(f"Монстр атакует магией: {actual_damage} урона тебе")

        # Эффект проклятия
        curse_damage = player.curse_effect()
        if curse_damage > 0:
            battle_log.append(f"Проклятие наносит {curse_damage} урона")

        if not player.is_alive():
            battle_log.append("💀 Ты проиграл...")
            break

        turn += 1
        if turn > 20:
            battle_log.append("Бой затянулся... Ничья!")
            break

    player.hp = player.max_hp
    await message.reply("\n".join(battle_log))

dp.register_message_handler(start, commands=['start'])
dp.register_message_handler(help_command, commands=['help'])
dp.register_message_handler(echo, commands=['echo'])
dp.register_message_handler(dice, commands=['dice'])
dp.register_message_handler(coinflip, commands=['coinflip'])
dp.register_message_handler(battle, commands=['battle'])

if __name__ == '__main__':
    executor.start_polling(dp)