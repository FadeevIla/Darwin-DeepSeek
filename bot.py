from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from core import environ_map
import random
import logging

logger = logging.getLogger(__name__)
BOT_TOKEN = environ_map['TELEGRAM_BOT_TOKEN']

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

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
        self.location = "таверна"

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
                           "Используй /help для списка команд.")
    else:
        await message.reply("Ты уже в игре! Используй /help для списка команд.")

async def help_command(message: types.Message):
    await message.reply("Доступные команды:\n"
                       "/start - начать игру\n"
                       "/help - эта справка\n"
                       "/echo <текст> - повторить текст\n"
                       "/dice - бросить кубик\n"
                       "/coinflip - подбросить монетку\n"
                       "/battle - начать битву с монстром\n"
                       "/status - характеристики персонажа\n"
                       "/inventory - инвентарь\n"
                       "/use <предмет> - использовать предмет\n"
                       "/shop - магазин\n"
                       "/buy <предмет> - купить предмет")

async def echo(message: types.Message):
    text = message.get_args()
    if text:
        await message.reply(text)
    else:
        await message.reply("Напиши текст после /echo")

async def dice(message: types.Message):
    result = random.randint(1, 6)
    await message.reply(f"🎲 Выпало: {result}")

async def coinflip(message: types.Message):
    result = random.choice(["Орёл", "Решка"])
    await message.reply(f"🪙 {result}")

async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    
    monster_hp = random.randint(30, 80)
    monster_strength = random.randint(5, 15)
    monster_name = random.choice(["Гоблин", "Скелет", "Волк", "Зомби", "Бандит"])
    
    battle_log = f"⚔️ Битва с {monster_name}!\n"
    battle_log += f"Твоё HP: {char.hp}/{char.max_hp} | HP монстра: {monster_hp}\n\n"
    
    while char.is_alive() and monster_hp > 0:
        # Ход игрока
        attack_type = random.choice(["физическая", "магическая"])
        if attack_type == "физическая":
            damage = char.attack_physical()
            battle_log += f"Ты атакуешь физически и наносишь {damage} урона!\n"
        else:
            damage = char.attack_magical()
            battle_log += f"Ты атакуешь магией и наносишь {damage} урона!\n"
        
        monster_hp -= damage
        
        if monster_hp <= 0:
            break
        
        # Ход монстра
        monster_damage = monster_strength + random.randint(0, 5)
        actual_damage = char.defend(monster_damage)
        battle_log += f"{monster_name} атакует и наносит {actual_damage} урона!\n"
        
        # Эффект проклятия
        curse_damage = char.curse_effect()
        if curse_damage > 0:
            battle_log += f"Проклятие наносит {curse_damage} урона!\n"
    
    if char.is_alive():
        exp_reward = random.randint(10, 30)
        coin_reward = random.randint(5, 20)
        char.coins += coin_reward
        leveled_up = char.gain_exp(exp_reward)
        
        battle_log += f"\n🎉 Победа! Ты получил {exp_reward} опыта и {coin_reward} монет!"
        if leveled_up:
            battle_log += f"\n⬆️ Уровень повышен до {char.level}!"
        
        # Шанс получить предмет
        if random.random() < 0.3:
            loot = random.choice(["зелье здоровья", "эликсир силы", "зелье магии"])
            char.inventory.append(loot)
            battle_log += f"\n🎁 Ты нашёл {loot}!"
    else:
        battle_log += f"\n💀 Ты погиб в бою... HP восстановлено до 50%"
        char.hp = char.max_hp // 2
    
    await message.reply(battle_log)

async def status_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    status_text = f"📊 Статус персонажа:\n"
    status_text += f"Уровень: {char.level}\n"
    status_text += f"Опыт: {char.exp}/{char.exp_to_next}\n"
    status_text += f"HP: {char.hp}/{char.max_hp}\n"
    status_text += f"Сила: {char.strength}\n"
    status_text += f"Ловкость: {char.agility}\n"
    status_text += f"Магия: {char.magic}\n"
    status_text += f"Проклятие: {char.curse}\n"
    status_text += f"Монеты: {char.coins}\n"
    status_text += f"Локация: {char.location}"
    
    await message.reply(status_text)

async def inventory_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    if not char.inventory:
        await message.reply("🎒 Инвентарь пуст")
    else:
        items = "\n".join([f"- {item}" for item in char.inventory])
        await message.reply(f"🎒 Инвентарь:\n{items}")

async def use_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    item_name = message.get_args()
    if not item_name:
        await message.reply("Укажи предмет для использования. Пример: /use зелье здоровья")
        return
    
    result = char.use_item(item_name)
    await message.reply(result)

async def shop_command(message: types.Message):
    await message.reply("🏪 Магазин:\n"
                       "1. Зелье здоровья - 15 монет (восстанавливает 30 HP)\n"
                       "2. Эликсир силы - 25 монет (Сила +2)\n"
                       "3. Зелье магии - 25 монет (Магия +2)\n\n"
                       "Купить: /buy <название предмета>")

async def buy_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    item_name = message.get_args().lower()
    
    shop_items = {
        "зелье здоровья": 15,
        "эликсир силы": 25,
        "зелье магии": 25
    }
    
    if item_name not in shop_items:
        await message.reply("Такого предмета нет в магазине. Список: /shop")
        return
    
    price = shop_items[item_name]
    if char.coins < price:
        await message.reply(f"Недостаточно монет. Нужно: {price}, у тебя: {char.coins}")
        return
    
    char.coins -= price
    char.inventory.append(item_name)
    await message.reply(f"✅ Ты купил {item_name} за {price} монет")

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