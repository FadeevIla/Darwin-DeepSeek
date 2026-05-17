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
            {"text": "Ты встретил старого мудреца на дороге", "effect": "heal", "value": 20},
            {"text": "Ты нашел сундук с монетами", "effect": "coins", "value": 15},
            {"text": "На тебя напали разбойники!", "effect": "damage", "value": 15},
            {"text": "Ты провалился в яму с шипами", "effect": "damage", "value": 10},
            {"text": "Ты нашел зелье здоровья", "effect": "item", "value": "зелье здоровья"},
            {"text": "Ты получил благословение богов", "effect": "heal", "value": 40},
            {"text": "Ты ограбил караван", "effect": "coins", "value": 25},
            {"text": "Ты отравился ядовитым грибом", "effect": "damage", "value": 20},
            {"text": "Ты нашел эликсир силы", "effect": "item", "value": "эликсир силы"},
            {"text": "Ты попал в магический шторм", "effect": "curse", "value": 1}
        ]
        event = random.choice(events)
        result = event["text"]
        
        if event["effect"] == "heal":
            self.heal(event["value"])
            result += f"\n❤️ Ты восстановил {event['value']} HP"
        elif event["effect"] == "damage":
            self.hp -= event["value"]
            result += f"\n💔 Ты потерял {event['value']} HP"
        elif event["effect"] == "coins":
            self.coins += event["value"]
            result += f"\n💰 Ты получил {event['value']} монет"
        elif event["effect"] == "item":
            self.inventory.append(event["value"])
            result += f"\n🎒 Ты получил {event['value']}"
        elif event["effect"] == "curse":
            self.curse += event["value"]
            result += f"\n😈 Твое проклятие усилилось!"
        
        return result

players = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        players[user_id] = RPGCharacter(user_id)
        await message.reply(
            f"🎮 Добро пожаловать в Уроборос!\n\n"
            f"Твой персонаж создан:\n"
            f"⚔️ Сила: {players[user_id].strength}\n"
            f"🏃 Ловкость: {players[user_id].agility}\n"
            f"🔮 Магия: {players[user_id].magic}\n"
            f"😈 Проклятие: {players[user_id].curse}\n"
            f"❤️ HP: {players[user_id].hp}/{players[user_id].max_hp}\n"
            f"💰 Монеты: {players[user_id].coins}\n\n"
            f"Доступные команды:\n"
            f"/profile - профиль\n"
            f"/explore - исследовать\n"
            f"/shop - магазин\n"
            f"/inventory - инвентарь\n"
            f"/heal - использовать зелье здоровья\n"
            f"/dice - бросить кубик\n"
            f"/coinflip - подбросить монетку\n"
            f"/echo - эхо сообщение"
        )
    else:
        await message.reply("Ты уже в игре! Используй /help для списка команд.")

@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.reply(
        "📖 Доступные команды:\n\n"
        "🎮 RPG команды:\n"
        "/start - начать игру\n"
        "/profile - твой профиль\n"
        "/explore - исследовать мир\n"
        "/shop - магазин предметов\n"
        "/inventory - инвентарь\n"
        "/heal - использовать зелье здоровья\n\n"
        "🎲 Развлечения:\n"
        "/dice - бросить кубик (1-6)\n"
        "/coinflip - подбросить монетку\n"
        "/echo <текст> - повторить сообщение"
    )

@dp.message_handler(commands=['profile'])
async def profile(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    
    await message.reply(
        f"📊 Профиль персонажа:\n\n"
        f"Уровень: {char.level}\n"
        f"Опыт: {char.exp}/{char.exp_to_next}\n"
        f"❤️ HP: {char.hp}/{char.max_hp}\n"
        f"⚔️ Сила: {char.strength}\n"
        f"🏃 Ловкость: {char.agility}\n"
        f"🔮 Магия: {char.magic}\n"
        f"😈 Проклятие: {char.curse}\n"
        f"💰 Монеты: {char.coins}\n"
        f"📍 Локация: {char.location}\n"
        f"🎒 Предметов: {len(char.inventory)}"
    )

@dp.message_handler(commands=['explore'])
async def explore(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    
    if not char.is_alive():
        await message.reply("💀 Ты мертв! Используй /start чтобы начать заново.")
        return
    
    # Случайное событие
    event_result = char.random_event()
    
    # Проверка на проклятие
    curse_damage = char.curse_effect()
    curse_text = ""
    if curse_damage > 0:
        curse_text = f"\n😈 Проклятие наносит {curse_damage} урона!"
    
    # Проверка на смерть
    death_text = ""
    if not char.is_alive():
        death_text = "\n💀 Ты погиб в приключении!"
    
    # Опыт за исследование
    exp_gain = random.randint(5, 15)
    leveled_up = char.gain_exp(exp_gain)
    level_text = ""
    if leveled_up:
        level_text = f"\n🎉 Уровень повышен! Теперь ты {char.level} уровня!"
    
    await message.reply(
        f"🗺️ Ты отправляешься исследовать {char.location}...\n\n"
        f"{event_result}"
        f"{curse_text}"
        f"{death_text}"
        f"\n\n✨ Получено опыта: {exp_gain}"
        f"{level_text}"
    )

@dp.message_handler(commands=['shop'])
async def shop(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    items = [
        ("зелье здоровья", "buy_health"),
        ("эликсир силы", "buy_strength"),
        ("зелье магии", "buy_magic"),
        ("зелье ловкости", "buy_agility")
    ]
    
    for item_name, callback_data in items:
        keyboard.add(types.InlineKeyboardButton(
            f"{item_name} - {5 if item_name == 'зелье здоровья' else 8} монет",
            callback_data=callback_data
        ))
    
    await message.reply(
        f"🏪 Магазин\n\n"
        f"💰 Твои монеты: {char.coins}\n\n"
        f"Выбери предмет для покупки:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def process_buy(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in players:
        await callback_query.message.reply("Сначала начни игру через /start")
        await callback_query.answer()
        return
    
    char = players[user_id]
    item_map = {
        "buy_health": "зелье здоровья",
        "buy_strength": "эликсир силы",
        "buy_magic": "зелье магии",
        "buy_agility": "зелье ловкости"
    }
    
    item_name = item_map.get(callback_query.data)
    if not item_name:
        await callback_query.answer("Неизвестный предмет")
        return
    
    prices = {"зелье здоровья": 5, "эликсир силы": 8, "зелье магии": 8, "зелье ловкости": 8}
    price = prices.get(item_name, 5)
    
    if char.buy_item(item_name, price):
        if item_name == "зелье ловкости":
            char.agility += 2
        await callback_query.message.reply(f"✅ Ты купил {item_name} за {price} монет!")
    else:
        await callback_query.message.reply("❌ У тебя недостаточно монет!")
    
    await callback_query.answer()

@dp.message_handler(commands=['inventory'])
async def inventory(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    
    if not char.inventory:
        await message.reply("🎒 Твой инвентарь пуст!")
        return
    
    items_list = "\n".join([f"• {item}" for item in char.inventory])
    await message.reply(f"🎒 Инвентарь:\n\n{items_list}")

@dp.message_handler(commands=['heal'])
async def heal(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    
    if "зелье здоровья" in char.inventory:
        result = char.use_item("зелье здоровья")
        await message.reply(result)
    else:
        await message.reply("❌ У тебя нет зелья здоровья!")

@dp.message_handler(commands=['dice'])
async def dice(message: types.Message):
    result = random.randint(1, 6)
    await message.reply(f"🎲 Ты бросил кубик и выпало: {result}")

@dp.message_handler(commands=['coinflip'])
async def coinflip(message: types.Message):
    result = random.choice(["Орел", "Решка"])
    await message.reply(f"🪙 Монетка показала: {result}")

@dp.message_handler(commands=['echo'])
async def echo(message: types.Message):
    text = message.get_args()
    if not text:
        await message.reply("Напиши текст после команды, например: /echo Привет!")
        return
    await message.reply(text)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)