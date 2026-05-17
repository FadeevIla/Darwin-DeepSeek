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
        self.coins = 10
        self.inventory = []
        self.level = 1
        self.exp = 0
        self.exp_to_next = 20

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

    def gain_exp(self, amount):
        self.exp += amount
        while self.exp >= self.exp_to_next:
            self.level += 1
            self.exp -= self.exp_to_next
            self.exp_to_next += int(self.exp_to_next * 0.2)
            self.strength += 1
            self.agility += 1
            self.magic += 1
            self.max_hp += 10
            self.hp = self.max_hp
            return True
        return False

    def use_item(self, item_name):
        if item_name in self.inventory:
            self.inventory.remove(item_name)
            if item_name == "зелье здоровья":
                self.heal(30)
                return f"Ты выпил зелье здоровья и восстановил 30 HP (теперь {self.hp}/{self.max_hp})"
            elif item_name == "эликсир силы":
                self.strength += 2
                return "Ты выпил эликсир силы! Сила +2"
            elif item_name == "зелье магии":
                self.magic += 2
                return "Ты выпил зелье магии! Магия +2"
        return f"У тебя нет {item_name} в инвентаре"

characters = {}

async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        characters[user_id] = RPGCharacter(user_id)
        await message.reply("Добро пожаловать в Уроборос! Твой персонаж создан.\n"
                           f"Сила: {characters[user_id].strength}\n"
                           f"Ловкость: {characters[user_id].agility}\n"
                           f"Магия: {characters[user_id].magic}\n"
                           f"Проклятие: {characters[user_id].curse}\n"
                           f"Монеты: {characters[user_id].coins}\n"
                           f"Уровень: {characters[user_id].level}")
    else:
        await message.reply("Ты уже в игре! Используй /help для списка команд.")

async def help_command(message: types.Message):
    await message.reply("Доступные команды:\n"
                       "/start - Начать игру\n"
                       "/help - Помощь\n"
                       "/echo <текст> - Повторить текст\n"
                       "/dice - Бросить кубик\n"
                       "/coinflip - Подбросить монетку\n"
                       "/battle - Сразиться с монстром\n"
                       "/shop - Магазин торговца\n"
                       "/inventory - Посмотреть инвентарь\n"
                       "/status - Статус персонажа\n"
                       "/use <предмет> - Использовать предмет")

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
    result = random.choice(["Орёл", "Решка"])
    await message.reply(f"🪙 {result}")

async def status_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    player = characters[user_id]
    await message.reply(f"📊 Статус персонажа:\n"
                       f"Уровень: {player.level}\n"
                       f"Опыт: {player.exp}/{player.exp_to_next}\n"
                       f"HP: {player.hp}/{player.max_hp}\n"
                       f"Сила: {player.strength}\n"
                       f"Ловкость: {player.agility}\n"
                       f"Магия: {player.magic}\n"
                       f"Проклятие: {player.curse}\n"
                       f"Монеты: {player.coins}")

async def inventory_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    player = characters[user_id]
    if not player.inventory:
        await message.reply("🎒 Инвентарь пуст")
    else:
        items = "\n".join([f"- {item}" for item in player.inventory])
        await message.reply(f"🎒 Инвентарь:\n{items}")

async def use_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    player = characters[user_id]
    item_name = message.get_args().lower()
    if not item_name:
        await message.reply("Укажи предмет для использования. Например: /use зелье здоровья")
        return
    result = player.use_item(item_name)
    await message.reply(result)

async def shop_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    player = characters[user_id]
    items = {
        "зелье здоровья": 10,
        "эликсир силы": 15,
        "зелье магии": 15
    }
    text = "🏪 Лавка торговца\n\n"
    text += f"Твои монеты: {player.coins}\n\n"
    for item, price in items.items():
        text += f"{item}: {price} монет\n"
    text += "\n/buy <предмет> - Купить предмет"
    await message.reply(text)

async def buy_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    player = characters[user_id]
    item_name = message.get_args().lower()
    items = {
        "зелье здоровья": 10,
        "эликсир силы": 15,
        "зелье магии": 15
    }
    if item_name not in items:
        await message.reply(f"Такого товара нет в лавке. Доступно: {', '.join(items.keys())}")
        return
    price = items[item_name]
    if player.coins < price:
        await message.reply(f"Недостаточно монет. Нужно {price}, у тебя {player.coins}")
        return
    player.coins -= price
    player.inventory.append(item_name)
    await message.reply(f"✅ Ты купил {item_name} за {price} монет. Осталось: {player.coins}")

async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    
    player = characters[user_id]
    if not player.is_alive():
        await message.reply("Ты слишком слаб для боя! Используй /heal чтобы восстановить силы.")
        return

    # Создаём монстра
    monster_hp = 50 + player.level * 10
    monster_max_hp = monster_hp
    monster_strength = 5 + player.level * 2
    monster_magic = 3 + player.level

    battle_log = [f"⚔️ Бой с монстром (Уровень {player.level})"]
    battle_log.append(f"Твоё HP: {player.hp}/{player.max_hp}")
    battle_log.append(f"Монстр HP: {monster_hp}/{monster_max_hp}\n")

    turn = 1
    while player.is_alive() and monster_hp > 0:
        # Случайное событие во время боя
        random_event = random.random()
        if random_event < 0.1:
            if random.choice([True, False]):
                player.heal(20)
                battle_log.append("✨ Ты нашёл лечебную траву! HP +20")
            else:
                monster_hp -= 10
                battle_log.append("⚡ Обвал ранил монстра! -10 HP")

        # Ход игрока
        action = random.choice(["physical", "magical"])
        if action == "physical":
            damage = player.attack_physical()
            monster_hp -= damage
            battle_log.append(f"🗡️ Ты атакуешь мечом: {damage} урона монстру")
        else:
            damage = player.attack_magical()
            monster_hp -= damage
            battle_log.append(f"🔮 Ты атакуешь магией: {damage} урона монстру")

        if monster_hp <= 0:
            battle_log.append("\n🏆 Ты победил!")
            exp_reward = random.randint(10, 20 + player.level * 5)
            coin_reward = random.randint(5, 10 + player.level * 3)
            player.coins += coin_reward
            leveled_up = player.gain_exp(exp_reward)
            battle_log.append(f"Получено опыта: {exp_reward}")
            battle_log.append(f"Получено монет: {coin_reward}")
            if leveled_up:
                battle_log.append(f"🎉 Поздравляю! Ты достиг уровня {player.level}!")
                
            # Шанс получить предмет
            if random.random() < 0.3:
                loot = random.choice(["зелье здоровья", "эликсир силы", "зелье магии"])
                player.inventory.append(loot)
                battle_log.append(f"🎁 Ты нашёл {loot}!")
            break

        # Ход монстра
        monster_action = random.choice(["physical", "magical"])
        if monster_action == "physical":
            damage = monster_strength + random.randint(0, 5)
            actual_damage = player.defend(damage)
            battle_log.append(f"👊 Монстр атакует: {actual_damage} урона тебе")
        else:
            damage = monster_magic + random.randint(0, 5)
            actual_damage = player.defend(damage)
            battle_log.append(f"💥 Монстр атакует магией: {actual_damage} урона тебе")

        # Эффект проклятия
        curse_damage = player.curse_effect()
        if curse_damage > 0:
            battle_log.append(f"☠️ Проклятие наносит {curse_damage} урона")

        if not player.is_alive():
            battle_log.append("\n💀 Ты проиграл...")
            break

        turn += 1
        if turn > 20:
            battle_log.append("\nБой затянулся... Ничья!")
            break

    player.hp = max(1, player.hp)
    await message.reply("\n".join(battle_log))

dp.register_message_handler(start, commands=['start'])
dp.register_message_handler(help_command, commands=['help'])
dp.register_message_handler(echo, commands=['echo'])
dp.register_message_handler(dice, commands=['dice'])
dp.register_message_handler(coinflip, commands=['coinflip'])
dp.register_message_handler(battle, commands=['battle'])
dp.register_message_handler(status_command, commands=['status'])
dp.register_message_handler(inventory_command, commands=['inventory'])
dp.register_message_handler(use_command, commands=['use'])
dp.register_message_handler(shop_command, commands=['shop'])
dp.register_message_handler(buy_command, commands=['buy'])

if __name__ == '__main__':
    executor.start_polling(dp)