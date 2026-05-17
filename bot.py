from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from core import environ_map, update_notifier
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

# RPG система боя
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

    def __str__(self):
        return (f"HP: {self.hp}/{self.max_hp} | "
                f"Сила: {self.strength} | Ловкость: {self.agility} | "
                f"Магия: {self.magic} | Проклятие: {self.curse}")

player_characters = {}

async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        player_characters[user_id] = RPGCharacter(user_id)
        await message.reply(f"Привет, {message.from_user.first_name}!\n"
                           f"Твой персонаж создан:\n{player_characters[user_id]}\n\n"
                           f"Команды: /help, /echo, /dice, /coinflip, /battle")
    else:
        await message.reply(f"С возвращением, {message.from_user.first_name}!\n"
                           f"Твой персонаж:\n{player_characters[user_id]}")

async def help_command(message: types.Message):
    await message.reply("Доступные команды:\n"
                       "/start - Начать игру\n"
                       "/help - Помощь\n"
                       "/echo <текст> - Повторить текст\n"
                       "/dice - Бросить кубик\n"
                       "/coinflip - Подбросить монетку\n"
                       "/battle - Сразиться с монстром")

async def echo(message: types.Message):
    text = message.text.replace('/echo', '', 1).strip()
    if text:
        await message.reply(text)
    else:
        await message.reply("Напиши текст после команды /echo")

async def dice(message: types.Message):
    result = random.randint(1, 6)
    await message.reply(f"🎲 Выпало: {result}")

async def coinflip(message: types.Message):
    result = random.choice(['Орел', 'Решка'])
    await message.reply(f"🪙 {result}")

async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        player_characters[user_id] = RPGCharacter(user_id)
        await message.reply("Создан новый персонаж! Используй /start для просмотра характеристик.")

    player = player_characters[user_id]
    monster = RPGCharacter(0)
    monster.hp = 50 + random.randint(0, 30)
    monster.max_hp = monster.hp

    battle_log = []
    turn = 1

    while player.is_alive() and monster.is_alive():
        battle_log.append(f"\n--- Раунд {turn} ---")

        # Ход игрока
        attack_type = random.choice(['physical', 'magical'])
        if attack_type == 'physical':
            damage = player.attack_physical()
            actual_damage = monster.defend(damage)
            battle_log.append(f"Ты атакуешь физически: {actual_damage} урона")
        else:
            damage = player.attack_magical()
            actual_damage = monster.defend(damage)
            battle_log.append(f"Ты атакуешь магией: {actual_damage} урона")

        # Проклятие игрока
        curse_damage = player.curse_effect()
        if curse_damage > 0:
            battle_log.append(f"Проклятие наносит {curse_damage} урона")

        if not monster.is_alive():
            battle_log.append("🎉 Ты победил монстра!")
            break

        # Ход монстра
        monster_attack = random.choice(['physical', 'magical'])
        if monster_attack == 'physical':
            damage = monster.attack_physical()
            actual_damage = player.defend(damage)
            battle_log.append(f"Монстр атакует физически: {actual_damage} урона")
        else:
            damage = monster.attack_magical()
            actual_damage = player.defend(damage)
            battle_log.append(f"Монстр атакует магией: {actual_damage} урона")

        # Проклятие монстра
        curse_damage = monster.curse_effect()
        if curse_damage > 0:
            battle_log.append(f"Проклятие монстра наносит {curse_damage} урона")

        if not player.is_alive():
            battle_log.append("💀 Ты проиграл...")
            break

        turn += 1
        if turn > 20:
            battle_log.append("Бой затянулся... Ничья!")
            break

    # Восстановление после боя
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