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
                           "Используй /help для списка команд.\n"
                           "Ты начинаешь в таверне. Используй /travel чтобы отправиться в путешествие!")
    else:
        await message.reply("Ты уже создал персонажа! Используй /help для списка команд.")

async def help_command(message: types.Message):
    await message.reply("🏰 Команды Уроборос:\n"
                       "/start - Создать персонажа\n"
                       "/help - Эта справка\n"
                       "/status - Твой статус\n"
                       "/inventory - Инвентарь\n"
                       "/use <предмет> - Использовать предмет\n"
                       "/shop - Магазин\n"
                       "/buy <предмет> - Купить предмет\n"
                       "/travel - Отправиться в путешествие\n"
                       "/echo <текст> - Повторить текст\n"
                       "/dice - Бросить кубик\n"
                       "/coinflip - Подбросить монету")

async def travel(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    
    # Случайные события
    events = [
        {"name": "монстры", "chance": 0.3, "text": "⚔️ На тебя напали дикие монстры!"},
        {"name": "сокровище", "chance": 0.2, "text": "💎 Ты нашел сундук с сокровищами!"},
        {"name": "торговец", "chance": 0.15, "text": "👤 Ты встретил странствующего торговца!"},
        {"name": "ловушка", "chance": 0.15, "text": "⚠️ Ты попал в ловушку!"},
        {"name": "источник", "chance": 0.1, "text": "🌊 Ты нашел целебный источник!"},
        {"name": "ничего", "chance": 0.1, "text": "🌿 Путешествие проходит спокойно..."}
    ]
    
    # Выбор события
    roll = random.random()
    current_chance = 0
    chosen_event = events[-1]
    
    for event in events:
        current_chance += event["chance"]
        if roll <= current_chance:
            chosen_event = event
            break
    
    # Обработка проклятия
    curse_text = ""
    if char.curse > 0 and random.random() < 0.3:
        damage = char.curse_effect()
        curse_text = f"\n🐍 Кольцо Уроборос жалит тебя! -{damage} HP"
    
    # Выполнение события
    result_text = chosen_event["text"]
    if chosen_event["name"] == "монстры":
        monster_hp = random.randint(20, 40)
        monster_strength = random.randint(5, 10)
        damage_to_char = max(1, monster_strength - char.agility // 4)
        char.hp -= damage_to_char
        damage_to_monster = char.attack_physical()
        result_text = f"⚔️ Ты сражаешься с монстром!\nМонстр нанес {damage_to_char} урона\nТы нанес {damage_to_monster} урона"
        if char.gain_exp(random.randint(5, 15)):
            result_text += "\n🌟 Ты повысил уровень!"
            curse_text += f"\n🐍 Проклятие усилилось! +1"
            char.curse += 1
    
    elif chosen_event["name"] == "сокровище":
        coins_found = random.randint(5, 20)
        char.coins += coins_found
        result_text = f"💎 Ты нашел {coins_found} монет!"
        if random.random() < 0.3:
            item = random.choice(["зелье здоровья", "эликсир силы", "зелье магии"])
            char.inventory.append(item)
            result_text += f"\n📦 А также {item}!"
    
    elif chosen_event["name"] == "торговец":
        if char.coins >= 10:
            char.coins -= 10
            item = random.choice(["зелье здоровья", "эликсир силы"])
            char.inventory.append(item)
            result_text = f"👤 Ты купил {item} за 10 монет!"
        else:
            result_text = "👤 У тебя недостаточно монет, чтобы что-то купить."
    
    elif chosen_event["name"] == "ловушка":
        damage = random.randint(10, 25) - char.agility // 5
        damage = max(1, damage)
        char.hp -= damage
        result_text = f"⚠️ Ты попал в ловушку! -{damage} HP"
    
    elif chosen_event["name"] == "источник":
        heal_amount = random.randint(20, 40)
        char.heal(heal_amount)
        result_text = f"🌊 Ты восстановил {heal_amount} HP!"
    
    # Проверка смерти
    if not char.is_alive():
        char.hp = 1
        result_text += "\n💀 Ты чуть не погиб! Кольцо сохранило тебе жизнь, но проклятие усилилось..."
        char.curse += 2
    
    await message.reply(f"🚶 Ты отправляешься в путь...\n\n{result_text}{curse_text}\n\nHP: {char.hp}/{char.max_hp} | Монеты: {char.coins} | Уровень: {char.level} | Проклятие: {char.curse}")

async def echo(message: types.Message):
    text = message.get_args()
    if not text:
        await message.reply("Напиши что-нибудь после /echo")
        return
    await message.reply(f"Эхо: {text}")

async def dice(message: types.Message):
    result = random.randint(1, 6)
    await message.reply(f"🎲 Ты выбросил: {result}")

async def coinflip(message: types.Message):
    result = random.choice(["Орел", "Решка"])
    await message.reply(f"🪙 Результат: {result}")

async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    monster_hp = random.randint(30, 60)
    monster_strength = random.randint(5, 12)
    
    result_lines = [f"⚔️ Битва началась! Монстр: HP {monster_hp}, Сила {monster_strength}"]
    
    round_num = 1
    while char.is_alive() and monster_hp > 0:
        action = random.choice(["атака", "защита", "магия"])
        
        if action == "атака":
            damage = char.attack_physical()
            monster_hp -= damage
            result_lines.append(f"Раунд {round_num}: Ты атаковал! -{damage} HP монстру")
        elif action == "магия":
            damage = char.attack_magical()
            monster_hp -= damage
            result_lines.append(f"Раунд {round_num}: Ты использовал магию! -{damage} HP монстру")
        else:
            monster_damage = max(1, monster_strength - char.agility // 2)
            char.hp -= monster_damage
            result_lines.append(f"Раунд {round_num}: Ты защищался! -{monster_damage} HP")
        
        # Монстр атакует
        if monster_hp > 0:
            monster_damage = max(1, monster_strength - char.agility // 4 + random.randint(-2, 2))
            char.hp -= monster_damage
            result_lines.append(f"Раунд {round_num}: Монстр атакует! -{monster_damage} HP")
        
        # Проклятие
        if char.curse > 0 and random.random() < 0.2:
            curse_damage = char.curse_effect()
            result_lines.append(f"🐍 Проклятие! -{curse_damage} HP")
        
        round_num += 1
    
    # Результат
    exp_gain = random.randint(10, 20)
    if char.is_alive():
        result_lines.append(f"\n🏆 Ты победил монстра! +{exp_gain} опыта")
        if char.gain_exp(exp_gain):
            result_lines.append("🌟 Ты повысил уровень!")
            char.curse += 1
            result_lines.append("🐍 Проклятие усилилось!")
    else:
        result_lines.append("\n💀 Ты погиб в бою...")
        result_lines.append("🐍 Кольцо пробудилось и восстановило тебя!")
        char.hp = char.max_hp // 2
        char.curse += 2
    
    await message.reply("\n".join(result_lines))

async def status_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    await message.reply(f"📊 Статус персонажа:\n"
                       f"Уровень: {char.level}\n"
                       f"Опыт: {char.exp}/{char.exp_to_next}\n"
                       f"HP: {char.hp}/{char.max_hp}\n"
                       f"Сила: {char.strength}\n"
                       f"Ловкость: {char.agility}\n"
                       f"Магия: {char.magic}\n"
                       f"Монеты: {char.coins}\n"
                       f"Проклятие: {char.curse}\n"
                       f"Предметы: {', '.join(char.inventory) if char.inventory else 'пусто'}")

async def inventory_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    if not char.inventory:
        await message.reply("📦 В твоем инвентаре пусто.")
    else:
        items_list = "\n".join([f"- {item}" for item in char.inventory])
        await message.reply(f"📦 Инвентарь:\n{items_list}")

async def use_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    args = message.get_args()
    if not args:
        await message.reply("Используй: /use <название предмета>")
        return
    
    result = char.use_item(args)
    await message.reply(result)

async def shop_command(message: types.Message):
    await message.reply("🏪 Магазин:\n"
                       "1. Зелье здоровья (15 монет) - /buy зелье здоровья\n"
                       "2. Эликсир силы (20 монет) - /buy эликсир силы\n"
                       "3. Зелье магии (20 монет) - /buy зелье магии")

async def buy_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return
    
    char = characters[user_id]
    
    prices = {
        "зелье здоровья": 15,
        "эликсир силы": 20,
        "зелье магии": 20
    }
    
    item_name = message.get_args()
    if not item_name or item_name not in prices:
        await message.reply("Такого товара нет! Доступно: зелье здоровья, эликсир силы, зелье магии")
        return
    
    price = prices[item_name]
    if char.coins < price:
        await message.reply(f"Недостаточно монет. Нужно: {price}, у тебя: {char.coins}")
        return
    
    char.coins -= price
    char.inventory.append(item_name)
    await message.reply(f"✅ Ты купил {item_name} за {price} монет")

dp.register_message_handler(start, commands=['start'])
dp.register_message_handler(help_command, commands=['help'])
dp.register_message_handler(travel, commands=['travel'])
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