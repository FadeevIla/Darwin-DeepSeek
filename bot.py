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

# RPG система боя с инвентарём
class RPGCharacter:
    def __init__(self, user_id):
        self.user_id = user_id
        self.strength = random.randint(5, 15)
        self.agility = random.randint(5, 15)
        self.magic = random.randint(5, 15)
        self.curse = random.randint(0, 5)
        self.hp = 100
        self.max_hp = 100
        self.inventory = []
        self.gold = 0

    def add_item(self, item):
        self.inventory.append(item)

    def remove_item(self, item_name):
        for item in self.inventory:
            if item['name'] == item_name:
                self.inventory.remove(item)
                return True
        return False

    def attack_physical(self):
        damage = self.strength + random.randint(0, 5)
        weapon_bonus = 0
        for item in self.inventory:
            if item['type'] == 'weapon':
                weapon_bonus += item['value']
        damage += weapon_bonus
        if self.curse > 0:
            damage -= self.curse // 2
        return max(1, damage)

    def attack_magical(self):
        damage = self.magic + random.randint(0, 10)
        magic_bonus = 0
        for item in self.inventory:
            if item['type'] == 'magic':
                magic_bonus += item['value']
        damage += magic_bonus
        if self.curse > 0:
            damage -= self.curse
        return max(1, damage)

    def defend(self, damage):
        reduction = self.agility // 3
        armor_reduction = 0
        for item in self.inventory:
            if item['type'] == 'armor':
                armor_reduction += item['value']
        actual_damage = max(1, damage - reduction - armor_reduction)
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

    def use_item(self, item_name):
        for item in self.inventory:
            if item['name'] == item_name and item['type'] == 'potion':
                self.heal(item['value'])
                self.inventory.remove(item)
                return f"Ты выпил зелье '{item_name}' и восстановил {item['value']} HP"
        return f"У тебя нет '{item_name}' в инвентаре или это не зелье"

    def show_inventory(self):
        if not self.inventory:
            return "Инвентарь пуст"
        result = "Инвентарь:\n"
        for item in self.inventory:
            result += f"▫️ {item['name']} ({item['type']}, сила: {item['value']})\n"
        if self.gold > 0:
            result += f"💰 Золото: {self.gold}"
        return result

    def __str__(self):
        return (f"HP: {self.hp}/{self.max_hp} | "
                f"Сила: {self.strength} | Ловкость: {self.agility} | "
                f"Магия: {self.magic} | Проклятие: {self.curse} | "
                f"💰 {self.gold} монет | Предметов: {len(self.inventory)}")

class Monster:
    def __init__(self, player_curse):
        self.strength = random.randint(8, 20) + player_curse
        self.agility = random.randint(5, 15)
        self.magic = random.randint(5, 15)
        self.curse = random.randint(0, 5)
        self.hp = 50 + player_curse * 5
        self.max_hp = self.hp
        self.name = random.choice(["Гоблин", "Волк", "Тролль", "Скелет", "Зомби", "Бандит"])

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

    def curse_effect(self):
        if self.curse > 0:
            self.hp -= self.curse
            return self.curse
        return 0

# Список возможных предметов для дропа
LOOT_TABLE = [
    {"name": "Железный меч", "type": "weapon", "value": 5, "price": 20},
    {"name": "Серебряный меч", "type": "weapon", "value": 10, "price": 50},
    {"name": "Деревянный щит", "type": "armor", "value": 3, "price": 15},
    {"name": "Стальной щит", "type": "armor", "value": 6, "price": 40},
    {"name": "Амулет магии", "type": "magic", "value": 5, "price": 30},
    {"name": "Посох силы", "type": "magic", "value": 8, "price": 60},
    {"name": "Зелье здоровья (малое)", "type": "potion", "value": 20, "price": 10},
    {"name": "Зелье здоровья (большое)", "type": "potion", "value": 50, "price": 25},
    {"name": "Золотой самородок", "type": "special", "value": 0, "price": 100},
    {"name": "Кольцо удачи", "type": "special", "value": 0, "price": 200}
]

player_characters = {}

async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        player_characters[user_id] = RPGCharacter(user_id)
        await message.reply(f"Привет, {message.from_user.first_name}!\n"
                           f"Твой персонаж создан:\n{player_characters[user_id]}\n\n"
                           f"Команды: /help, /echo, /dice, /coinflip, /battle, /inventory, /use, /shop")
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
                       "/battle - Сразиться с монстром\n"
                       "/inventory - Посмотреть инвентарь\n"
                       "/use <название> - Использовать предмет\n"
                       "/shop - Купить предмет")

async def echo(message: types.Message):
    text = message.text.replace('/echo', '', 1).strip()
    if text:
        await message.reply(text)
    else:
        await message.reply("Напиши что-нибудь после /echo")

async def dice(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    result = random.randint(1, 20)
    await message.reply(f"🎲 Ты выбросил {result}!")

async def coinflip(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    result = random.choice(["Орёл", "Решка"])
    await message.reply(f"🪙 Выпал {result}!")

async def inventory(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    player = player_characters[user_id]
    await message.reply(player.show_inventory())

async def use_item(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    player = player_characters[user_id]
    item_name = message.text.replace('/use', '', 1).strip()
    if not item_name:
        await message.reply("Напиши название предмета: /use <название>")
        return
    result = player.use_item(item_name)
    await message.reply(result)

async def shop(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    player = player_characters[user_id]

    shop_text = "🛒 Лавка торговца:\n"
    shop_text += "Товары для продажи (цена в монетах):\n\n"

    items_by_type = {"weapon": [], "armor": [], "magic": [], "potion": [], "special": []}
    for item in LOOT_TABLE:
        items_by_type[item['type']].append(item)

    for item_type, items in items_by_type.items():
        type_names = {
            "weapon": "Оружие", "armor": "Броня", "magic": "Магия", "potion": "Зелья", "special": "Особые"
        }
        shop_text += f"📦 {type_names[item_type]}:\n"
        for item in items:
            shop_text += f"▫️ {item['name']} - {item['price']} монет\n"
        shop_text += "\n"

    shop_text += f"У тебя: {player.gold} монет\n"
    shop_text += "Купить: /buy <название>\n"
    shop_text += "Продать: /sell <название>"

    await message.reply(shop_text)

async def buy(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    player = player_characters[user_id]

    item_name = message.text.replace('/buy', '', 1).strip()
    if not item_name:
        await message.reply("Напиши название предмета: /buy <название>")
        return

    item_to_buy = None
    for item in LOOT_TABLE:
        if item['name'].lower() == item_name.lower():
            item_to_buy = item
            break

    if not item_to_buy:
        await message.reply(f"Предмет '{item_name}' не найден в лавке")
        return

    if player.gold < item_to_buy['price']:
        await message.reply(f"Недостаточно золота! Нужно {item_to_buy['price']} монет")
        return

    player.gold -= item_to_buy['price']
    player.add_item(item_to_buy.copy())
    await message.reply(f"✅ Куплен {item_to_buy['name']} за {item_to_buy['price']} монет")

async def sell(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    player = player_characters[user_id]

    item_name = message.text.replace('/sell', '', 1).strip()
    if not item_name:
        await message.reply("Напиши название предмета: /sell <название>")
        return

    item_to_sell = None
    for item in player.inventory:
        if item['name'].lower() == item_name.lower():
            item_to_sell = item
            break

    if not item_to_sell:
        await message.reply(f"Предмет '{item_name}' не найден в инвентаре")
        return

    sell_price = item_to_sell['price'] // 2
    player.gold += sell_price
    player.inventory.remove(item_to_sell)
    await message.reply(f"✅ Продан {item_to_sell['name']} за {sell_price} монет")

async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in player_characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    player = player_characters[user_id]
    monster = Monster(player.curse)

    battle_log = [f"⚔️ Бой с {monster.name}!\n"]
    battle_log.append(f"{player}")
    battle_log.append(f"{monster.name}: HP {monster.hp}/{monster.max_hp}\n")

    turn = 0
    while player.is_alive() and monster.is_alive():
        if random.choice([True, False]):
            damage = player.attack_physical()
            actual = monster.defend(damage)
            battle_log.append(f"Ты атакуешь физически: {actual} урона {monster.name}")
        else:
            damage = player.attack_magical()
            actual = monster.defend(damage)
            battle_log.append(f"Ты атакуешь магией: {actual} урона {monster.name}")

        if not monster.is_alive():
            battle_log.append(f"🏆 Ты победил {monster.name}!")
            gold_reward = random.randint(10, 30) + player.curse * 2
            player.gold += gold_reward
            battle_log.append(f"💰 Получено {gold_reward} монет")

            # Дроп предмета с шансом 40%
            if random.random() < 0.4:
                loot = random.choice(LOOT_TABLE)
                player.add_item(loot.copy())
                battle_log.append(f"📦 Выпал предмет: {loot['name']}!")
            break

        if random.choice([True, False]):
            damage = monster.attack_physical()
            actual = player.defend(damage)
            battle_log.append(f"{monster.name} атакует физически: {actual} урона")
        else:
            damage = monster.attack_magical()
            actual = player.defend(damage)
            battle_log.append(f"{monster.name} атакует магией: {actual} урона")

        curse_damage = monster.curse_effect()
        if curse_damage > 0:
            battle_log.append(f"Проклятие {monster.name} наносит {curse_damage} урона")

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
dp.register_message_handler(inventory, commands=['inventory'])
dp.register_message_handler(use_item, commands=['use'])
dp.register_message_handler(shop, commands=['shop'])
dp.register_message_handler(buy, commands=['buy'])
dp.register_message_handler(sell, commands=['sell'])
dp.register_message_handler(battle, commands=['battle'])

if __name__ == '__main__':
    executor.start_polling(dp)