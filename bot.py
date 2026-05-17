import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from core import environ_map

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

    def buy_item(self, item_name, price):
        if self.coins >= price:
            self.coins -= price
            self.inventory.append(item_name)
            return True
        return False

    def random_event(self):
        events = [
            {"text": "Ты встретил старого мудреца на перекрестке. Он дарует тебе мудрость!", "effect": lambda: self.strength + 1},
            {"text": "Грабители напали на тебя! Ты потерял немного монет.", "effect": lambda: setattr(self, 'coins', max(0, self.coins - random.randint(1, 5)))},
            {"text": "Ты нашёл старый сундук с сокровищами!", "effect": lambda: setattr(self, 'coins', self.coins + random.randint(5, 15))},
            {"text": "Загадочная фигура предлагает тебе зелье здоровья в обмен на монеты.", "effect": lambda: self.buy_item("зелье здоровья", 5) or setattr(self, 'coins', self.coins)},
            {"text": "Проклятие кольца усиливается! Ты чувствуешь боль.", "effect": lambda: setattr(self, 'curse', min(10, self.curse + 1))},
            {"text": "Ты наткнулся на банду разбойников! Придётся сражаться.", "effect": lambda: None},
        ]
        return random.choice(events)

    def get_status(self):
        return (f"⚔️ Статус персонажа:\n"
                f"💪 Сила: {self.strength}\n"
                f"🏃 Ловкость: {self.agility}\n"
                f"🔮 Магия: {self.magic}\n"
                f"❤️ HP: {self.hp}/{self.max_hp}\n"
                f"🪙 Монеты: {self.coins}\n"
                f"📦 Инвентарь: {', '.join(self.inventory) if self.inventory else 'пусто'}\n"
                f"📊 Уровень: {self.level}\n"
                f"✨ Опыт: {self.exp}/{self.exp_to_next}\n"
                f"☠️ Проклятие: {self.curse}/10\n"
                f"📍 Локация: {self.location}")

characters = {}

async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        characters[user_id] = RPGCharacter(user_id)
        await message.reply("Добро пожаловать в Уроборос! Твой персонаж создан.\n"
                           "Используй /help для списка команд.")
    else:
        await message.reply("Ты уже в игре! Используй /help для команд.")

async def help_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    await message.reply(f"Доступные команды:\n"
                       f"/status — твой статус\n"
                       f"/battle — сразиться с врагом\n"
                       f"/shop — магазин\n"
                       f"/use <предмет> — использовать предмет\n"
                       f"/travel — отправиться в путь (может случиться событие)\n"
                       f"/curse — информация о проклятии\n"
                       f"/help — эта справка")

async def status_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    await message.reply(char.get_status())

async def shop_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    if char.location != "таверна":
        await message.reply("Ты не в таверне! Вернись через /travel или используй /status чтобы узнать локацию.")
        return
    items = [
        {"name": "зелье здоровья", "price": 10, "desc": "Восстанавливает 30 HP"},
        {"name": "эликсир силы", "price": 20, "desc": "Сила +2"},
        {"name": "зелье магии", "price": 20, "desc": "Магия +2"},
    ]
    response = "🏪 Таверна — Магазин:\n\n"
    for idx, item in enumerate(items, 1):
        response += f"{idx}. {item['name'].capitalize()} — {item['price']} монет — {item['desc']}\n"
    response += f"\nУ тебя {char.coins} монет.\nИспользуй /buy <номер> для покупки."

async def buy_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    if char.location != "таверна":
        await message.reply("Ты не в таверне!")
        return
    try:
        args = message.get_args().split()
        if not args:
            await message.reply("Укажи номер товара: /buy <номер>")
            return
        item_index = int(args[0]) - 1
        items = [
            {"name": "зелье здоровья", "price": 10},
            {"name": "эликсир силы", "price": 20},
            {"name": "зелье магии", "price": 20},
        ]
        if 0 <= item_index < len(items):
            item = items[item_index]
            if char.buy_item(item["name"], item["price"]):
                await message.reply(f"Ты купил {item['name']} за {item['price']} монет!")
            else:
                await message.reply(f"Недостаточно монет! Нужно {item['price']}, у тебя {char.coins}.")
        else:
            await message.reply("Неверный номер предмета!")
    except (ValueError, IndexError):
        await message.reply("Используй: /buy <номер>")

async def use_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    try:
        args = message.get_args().split()
        if not args:
            await message.reply("Укажи предмет: /use <предмет>")
            return
        item_name = " ".join(args).lower()
        result = char.use_item(item_name)
        await message.reply(result)
    except Exception as e:
        await message.reply(f"Ошибка: {str(e)}")

async def travel_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    if not char.is_alive():
        await message.reply("Ты мёртв! Игра окончена.")
        return
    
    event = char.random_event()
    response = f"📍 Ты отправляешься в путь...\n{event['text']}"
    
    # Применение эффекта события
    if event["text"] == "Ты встретил старого мудреца на перекрестке. Он дарует тебе мудрость!":
        char.strength += 1
        response += "\n+1 к силе! Теперь она: " + str(char.strength)
    elif event["text"] == "Грабители напали на тебя! Ты потерял немного монет.":
        response += f"\nТвои монеты: {char.coins}"
    elif event["text"] == "Ты нашёл старый сундук с сокровищами!":
        response += f"\nТвои монеты: {char.coins}"
    elif event["text"] == "Загадочная фигура предлагает тебе зелье здоровья в обмен на монеты.":
        if char.coins >= 5:
            char.buy_item("зелье здоровья", 5)
            response += "\nЗелье здоровья добавлено в инвентарь!"
        else:
            response += "\nНе хватает монет для покупки..."
    elif event["text"] == "Проклятие кольца усиливается! Ты чувствуешь боль.":
        char.curse = min(10, char.curse + 1)
        char.hp -= 1
        response += f"\nПроклятие теперь {char.curse}/10, HP уменьшено на 1 (теперь {char.hp}/{char.max_hp})"
    
    # Смена локации случайно
    old_location = char.location
    locations = ["таверна", "лес", "горы", "болото", "город"]
    new_location = random.choice(locations)
    char.location = new_location
    response += f"\nТы оказался в {new_location}."
    
    # Опыт за путешествие
    if char.gain_exp(5):
        response += f"\n🎉 Поздравляю! Ты достиг уровня {char.level}! Все характеристики +1, HP увеличено!"
    
    await message.reply(response)

async def battle_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    if not char.is_alive():
        await message.reply("Ты мёртв! Игра окончена.")
        return
    
    # Создание врага
    enemy_hp = 20 + random.randint(0, 10) + char.level * 5
    enemy_max_hp = enemy_hp
    enemy_strength = 5 + random.randint(0, 5) + char.level // 2
    enemy_name = random.choice(["Гоблин", "Скелет", "Волк", "Бандит", "Зомби"])
    
    battle_log = f"⚔️ Бой с {enemy_name}!\nHP врага: {enemy_hp}\nТвоё HP: {char.hp}/{char.max_hp}\n\n"
    
    # Боевой цикл
    turn = 0
    while char.is_alive() and enemy_hp > 0:
        turn += 1
        
        # Сначала проклятие
        curse_damage = char.curse_effect()
        if curse_damage > 0:
            battle_log += f"Кольцо наносит {curse_damage} урона от проклятия!\n"
        
        if not char.is_alive():
            battle_log += "Ты погиб от проклятия кольца!\n"
            break
        
        # Выбор действия ИИ
        action = random.choice(["phys", "magic", "defend"])
        
        if action == "phys":
            damage = char.attack_physical()
            enemy_hp -= damage
            battle_log += f"Ты атакуешь физически и наносишь {damage} урона!\n"
        elif action == "magic":
            damage = char.attack_magical()
            enemy_hp -= damage
            battle_log += f"Ты атакуешь магией и наносишь {damage} урона!\n"
        elif action == "defend":
            battle_log += "Ты готовишься защищаться!\n"
        
        # Враг атакует
        if enemy_hp > 0:
            enemy_damage = enemy_strength + random.randint(0, 5)
            if action == "defend":
                actual_damage = char.defend(enemy_damage * 2)
                battle_log += f"Враг атакует с силой {enemy_damage}, но ты защищаешься! Получено {actual_damage} урона.\n"
            else:
                actual_damage = char.defend(enemy_damage)
                battle_log += f"Враг атакует с силой {enemy_damage}. Получено {actual_damage} урона.\n"
        
        if turn >= 10:
            battle_log += "Бой затянулся... Враг убегает!\n"
            enemy_hp = 0
            break
    
    if char.is_alive():
        # Награда
        exp_reward = 10 + random.randint(0, 10) + char.level * 2
        coin_reward = 5 + random.randint(0, 10) + char.level * 2
        char.coins += coin_reward
        battle_log += f"\n🎉 Победа! Ты получил {exp_reward} опыта и {coin_reward} монет!"
        
        if char.gain_exp(exp_reward):
            battle_log += f"\n🎉 Поздравляю! Ты достиг уровня {char.level}! Все характеристики +1, HP увеличено!"
        
        # Шанс усилить проклятие
        if random.randint(1, 5) == 1:
            char.curse = min(10, char.curse + 1)
            battle_log += f"\n☠️ Проклятие усилилось до {char.curse}/10!"
        
        # Шанс получить предмет
        if random.randint(1, 3) == 1:
            items = ["зелье здоровья", "эликсир силы", "зелье магии"]
            item = random.choice(items)
            char.inventory.append(item)
            battle_log += f"\n📦 Ты нашёл {item}!"
    else:
        battle_log += "\n💀 Ты погиб! Игра окончена."
    
    await message