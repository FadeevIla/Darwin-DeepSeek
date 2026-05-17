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

players = {}

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
        self.fate_points = 0

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
        leveled_up = False
        while self.exp >= self.exp_to_next:
            self.level += 1
            self.exp -= self.exp_to_next
            self.exp_to_next += int(self.exp_to_next * 0.2)
            self.strength += 1
            self.agility += 1
            self.magic += 1
            self.max_hp += 10
            self.hp = self.max_hp
            leveled_up = True
        return leveled_up

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
            {"text": "Ты встретил старого мудреца на дороге. Он дал тебе карту сокровищ.", "effect": "inventory", "item": "карта сокровищ"},
            {"text": "Внезапный обвал! Ты чуть не погиб, но успел отскочить. Теряешь 10 HP.", "effect": "damage", "amount": 10},
            {"text": "Ты нашел старый сундук с монетами. +5 монет!", "effect": "coins", "amount": 5},
            {"text": "Загадочный странник предлагает тебе проверить судьбу. Рискнешь?", "effect": "choice", "question": "Принять вызов судьбы?", "positive": {"text": "Ты выиграл! +20 монет и +10 HP", "coins": 20, "heal": 10}, "negative": {"text": "Ты проиграл. -15 HP и чувствуешь, как кольцо сжимается.", "damage": 15, "curse": 1}},
            {"text": "Ты находишь заброшенную кузницу. Кузнец может улучшить твое оружие за 10 монет.", "effect": "blacksmith", "price": 10},
        ]
        return random.choice(events)

    def handle_event(self, event):
        if event["effect"] == "inventory":
            self.inventory.append(event["item"])
            return event["text"]
        elif event["effect"] == "damage":
            self.hp -= event["amount"]
            return event["text"]
        elif event["effect"] == "coins":
            self.coins += event["amount"]
            return event["text"]
        elif event["effect"] == "choice":
            return {"question": event["question"], "positive": event["positive"], "negative": event["negative"]}
        elif event["effect"] == "blacksmith":
            return {"text": event["text"], "price": event["price"]}

    def answer_choice(self, choice, event_data):
        if choice == "yes":
            for key, value in event_data["positive"].items():
                if key == "coins":
                    self.coins += value
                elif key == "heal":
                    self.heal(value)
                elif key == "curse":
                    self.curse += value
                elif key == "damage":
                    self.hp -= value
            return event_data["positive"]["text"]
        else:
            return "Ты отказался от вызова. Ничего не произошло."

    def buy_blacksmith(self, price):
        if self.coins >= price:
            self.coins -= price
            self.strength += 2
            return "Кузнец улучшил твое оружие. Сила +2!"
        return "У тебя недостаточно монет."

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        players[user_id] = RPGCharacter(user_id)
    char = players[user_id]
    text = f"🏰 Добро пожаловать в Уроборос, {message.from_user.first_name}!\nТы в таверне. Вот твои характеристики:\nHP: {char.hp}/{char.max_hp}\nСила: {char.strength}\nЛовкость: {char.agility}\nМагия: {char.magic}\nПроклятие: {char.curse}\nМонеты: {char.coins}\nУровень: {char.level}\nОпыт: {char.exp}/{char.exp_to_next}\n\nИспользуй /help для списка команд."
    await message.reply(text)

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    text = "📜 Команды Уробороса:\n/start — начать игру\n/profile — твой профиль\n/inventory — инвентарь\n/shop — магазин\n/battle — сражение с монстром\n/explore — случайное событие\n/heal — использовать зелье здоровья\n/curse — проверить проклятие\n/fate — испытать судьбу\n/level — информация об уровне"
    await message.reply(text)

@dp.message_handler(commands=['profile'])
async def profile(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала напиши /start")
        return
    char = players[user_id]
    text = f"📊 Профиль {message.from_user.first_name}:\nHP: {char.hp}/{char.max_hp}\nСила: {char.strength}\nЛовкость: {char.agility}\nМагия: {char.magic}\nПроклятие: {char.curse}\nМонеты: {char.coins}\nУровень: {char.level}\nОпыт: {char.exp}/{char.exp_to_next}\nЛокация: {char.location}"
    await message.reply(text)

@dp.message_handler(commands=['inventory'])
async def inventory(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала напиши /start")
        return
    char = players[user_id]
    if not char.inventory:
        await message.reply("🎒 Твой инвентарь пуст.")
    else:
        items = "\n".join(f"• {item}" for item in char.inventory)
        await message.reply(f"🎒 Инвентарь:\n{items}")

@dp.message_handler(commands=['shop'])
async def shop(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала напиши /start")
        return
    text = "🏪 Магазин:\n1. Зелье здоровья — 10 монет (/buy_health)\n2. Эликсир силы — 15 монет (/buy_strength)\n3. Зелье магии — 15 монет (/buy_magic)\n4. Улучшение оружия у кузнеца — 10 монет (/blacksmith)"
    await message.reply(text)

@dp.message_handler(commands=['buy_health'])
async def buy_health(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала напиши /start")
        return
    char = players[user_id]
    if char.buy_item("зелье здоровья", 10):
        await message.reply("✅ Ты купил зелье здоровья! Оно в инвентаре.")
    else:
        await message.reply("❌ Недостаточно монет!")

@dp.message_handler(commands=['buy_strength'])
async def buy_strength(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала напиши /start")
        return
    char = players[user_id]
    if char.buy_item("эликсир силы", 15):
        await message.reply("✅ Ты купил эликсир силы! Он в инвентаре.")
    else:
        await message.reply("❌ Недостаточно монет!")

@dp.message_handler(commands=['buy_magic'])
async def buy_magic(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала напиши /start")
        return
    char = players[user_id]
    if char.buy_item("зелье магии", 15):
        await message.reply("✅ Ты купил зелье магии! Оно в инвентаре.")
    else:
        await message.reply("❌ Недостаточно монет!")

@dp.message_handler(commands=['blacksmith'])
async def blacksmith(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала напиши /start")
        return
    char = players[user_id]
    result = char.buy_blacksmith(10)
    await message.reply(result)

@dp.message_handler(commands=['battle'])
async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала напиши /start")
        return
    char = players[user_id]
    if not char.is_alive():
        await message.reply("💀 Ты мертв. Используй /resurrect или начни заново /start")
        return
    monster_hp = random.randint(20, 40)
    monster_damage = random.randint(5, 15) + char.curse // 2
    monster_name = random.choice(["гоблин", "скелет", "волк", "зомби"])
    text = f"⚔️ Ты встретил {monster_name}! У него {monster_hp} HP.\nЧто будешь делать? /attack_phys, /attack_magic, /defend"
    await message.reply(text)
    players[user_id]._battle = {"monster_hp": monster_hp, "monster_damage": monster_damage, "monster_name": monster_name}

@dp.message_handler(commands=['attack_phys'])
async def attack_phys(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players or not hasattr(players[user_id], '_battle'):
        await message.reply("Нет битвы! Начни /battle")
        return
    char = players[user_id]
    if not char.is_alive():
        await message.reply("💀 Ты мертв.")
        return
    battle = char._battle
    damage = char.attack_physical()
    battle["monster_hp"] -= damage
    curse_damage = char.curse_effect()
    text = f"⚔️ Ты нанес {damage} урона {battle['monster_name']}!"
    if curse_damage > 0:
        text += f"\nКольцо забирает {curse_damage} HP у тебя."
    if battle["monster_hp"] <= 0:
        exp_gain = random.randint(10, 20)
        coin_gain = random.randint(5, 15)
        char.coins += coin_gain
        leveled = char.gain_exp(exp_gain)
        text += f"\n🏆 Ты победил! Получено {exp_gain} опыта и {coin_gain} монет."
        if leveled:
            text += f" 🎉 Уровень повышен до {char.level}!"
        del char._battle
    else:
        enemy_damage = random.randint(5, battle["monster_damage"])
        actual_damage = char.defend(enemy_damage)
        text += f"\n{battle['monster_name']} ранил тебя на {actual_damage} HP."
        if not char.is_alive():
            text += "\n💀 Ты погиб в бою!"
            del char._battle
        else:
            text += f"\nТвое HP: {char.hp}/{char.max_hp}"
    await message.reply(text)

@dp.message_handler(commands=['attack_magic'])
async def attack_magic(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players or not hasattr(players[user_id], '_battle'):
        await message.reply("Нет битвы! Начни /battle")
        return
    char = players[user_id]
    if not char.is_alive():
        await message.reply("💀 Ты мертв.")
        return
    battle = char._battle
    damage = char.attack_magical()
    battle["monster_hp"] -= damage
    curse_damage = char.curse_effect()
    text = f"🔮 Ты нанес {damage} магического урона {battle['monster_name']}!"
    if curse_damage > 0:
        text += f"\nКольцо забирает {curse_damage} HP у тебя."
    if battle["monster_hp"] <= 0:
        exp_gain = random.randint(10, 20)
        coin_gain = random.randint(5, 15)
        char.coins += coin_gain
        leveled = char.gain_exp(exp_gain)
        text += f"\n🏆 Ты победил! Получено {exp_gain} опыта и {coin_gain} монет."
        if leveled:
            text += f" 🎉 Уровень повышен до {char.level}!"
        del char._battle
    else:
        enemy_damage = random.randint(5, battle["monster_damage"])
        actual_damage = char.defend(enemy_damage)
        text += f"\n{battle['monster_name']} ранил тебя на {actual_damage} HP."
        if not char.is_alive():
            text += "\n💀 Ты погиб в бою!"
            del char._battle
        else:
            text += f"\nТвое HP: {char.hp}/{char.max_hp}"
    await message.reply(text)

@dp.message_handler(commands=['defend'])
async def defend(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players or not hasattr(players[user_id], '_battle'):
        await message.reply("Нет битвы! Начни /battle")
        return
    char = players[user_id]
    if not char.is_alive():
        await message.reply("💀 Ты мертв.")
        return
    battle = char._battle
    curse_damage = char.curse_effect()