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
            {"text": "Ты нашел сундук с сокровищами! +15 монет", "coins": 15, "hp": 0, "item": None},
            {"text": "На тебя напали разбойники! -10 HP", "coins": 0, "hp": -10, "item": None},
            {"text": "Ты встретил странника, он поделился зельем здоровья.", "coins": 0, "hp": 20, "item": "зелье здоровья"},
            {"text": "Ты провалился в яму! -15 HP", "coins": 0, "hp": -15, "item": None},
            {"text": "Старый мудрец дал тебе эликсир силы.", "coins": 0, "hp": 0, "item": "эликсир силы"},
            {"text": "Ты нашел кошелек с 20 монетами.", "coins": 20, "hp": 0, "item": None},
        ]
        return random.choice(events)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        players[user_id] = RPGCharacter(user_id)
        await message.reply("Добро пожаловать в Уроборос! Ты просыпаешься в таверне с древним кольцом на пальце.\n"
                           "Используй /status для проверки состояния, /explore для приключений, /battle для битвы.\n"
                           "Помни: кольцо медленно пожирает тебя...")
    else:
        await message.reply("Ты уже в игре. Используй /help для списка команд.")

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await message.reply("Команды Уробороса:\n"
                       "/start — начать игру\n"
                       "/status — твое состояние\n"
                       "/explore — отправиться в путешествие\n"
                       "/battle — вступить в бой\n"
                       "/attack — атаковать физически\n"
                       "/magic — атаковать магией\n"
                       "/defend — защищаться\n"
                       "/shop — посетить торговца\n"
                       "/buy <предмет> — купить предмет\n"
                       "/use <предмет> — использовать предмет\n"
                       "/inventory — инвентарь\n"
                       "/help — эта справка")

@dp.message_handler(commands=['status'])
async def status(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру /start")
        return
    char = players[user_id]
    curse_status = f"👿 Проклятие кольца: {char.curse}" if char.curse > 0 else "😇 Проклятие спит"
    inventory_str = ", ".join(char.inventory) if char.inventory else "пусто"
    await message.reply(f"⚔️ Уроборос — статус:\n"
                       f"Уровень: {char.level}\n"
                       f"Опыт: {char.exp}/{char.exp_to_next}\n"
                       f"HP: {char.hp}/{char.max_hp}\n"
                       f"Сила: {char.strength} | Ловкость: {char.agility} | Магия: {char.magic}\n"
                       f"Монеты: {char.coins}\n"
                       f"Инвентарь: {inventory_str}\n"
                       f"Локация: {char.location}\n"
                       f"{curse_status}")

@dp.message_handler(commands=['explore'])
async def explore(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру /start")
        return
    char = players[user_id]
    if not char.is_alive():
        await message.reply("💀 Ты мертв. Начни новую игру с /start")
        return
    event = char.random_event()
    text = event["text"]
    if event["coins"] > 0:
        char.coins += event["coins"]
        text += f" (теперь {char.coins} монет)"
    if event["hp"] > 0:
        char.heal(event["hp"])
        text += f" (восстановлено {event['hp']} HP)"
    elif event["hp"] < 0:
        char.hp += event["hp"]
        if char.hp <= 0:
            text += "\n💀 Ты погиб в путешествии!"
            char.hp = 0
    if event["item"]:
        char.inventory.append(event["item"])
        text += f" (получено {event['item']})"
    if char.curse > 0:
        curse_damage = random.randint(1, char.curse)
        char.hp -= curse_damage
        text += f"\nКольцо терзает тебя, отнимая {curse_damage} HP."
        if char.hp <= 0:
            text += "\n💀 Проклятие кольца убило тебя!"
            char.hp = 0
    exp_gain = random.randint(5, 15)
    leveled = char.gain_exp(exp_gain)
    text += f"\nОпыт: +{exp_gain}"
    if leveled:
        text += f"\n🎉 Уровень повышен до {char.level}!"
    await message.reply(text)

@dp.message_handler(commands=['battle'])
async def battle_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру /start")
        return
    char = players[user_id]
    if not char.is_alive():
        await message.reply("💀 Ты мертв.")
        return
    if hasattr(char, '_battle'):
        await message.reply("Ты уже в бою! Используй /attack, /magic или /defend")
        return
    monsters = [
        {"name": "гоблин", "hp": 30, "damage": 8, "coins": 10},
        {"name": "скелет", "hp": 40, "damage": 10, "coins": 15},
        {"name": "темный рыцарь", "hp": 60, "damage": 12, "coins": 25},
        {"name": "дракончик", "hp": 80, "damage": 15, "coins": 40},
    ]
    monster = random.choice(monsters)
    char._battle = {"monster": monster.copy(), "monster_name": monster["name"],
                    "monster_hp": monster["hp"], "monster_damage": monster["damage"],
                    "monster_coins": monster["coins"]}
    curse_damage = char.curse_effect()
    text = f"⚔️ На тебя напал {monster['name']} (HP: {monster['hp']})!"
    if curse_damage > 0:
        text += f"\nКольцо ранит тебя на {curse_damage} HP."
        if not char.is_alive():
            text += "\n💀 Кольцо убило тебя в начале битвы!"
            del char._battle
    await message.reply(text)

@dp.message_handler(commands=['attack'])
async def attack_physical(message: types.Message):
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
    text = f"🗡️ Ты ударил {battle['monster_name']} на {damage} урона (HP монстра: {battle['monster_hp']})"
    if curse_damage > 0:
        text += f"\nКольцо ранит тебя на {curse_damage} HP."
        if not char.is_alive():
            text += "\n💀 Кольцо убило тебя!"
            del char._battle
            await message.reply(text)
            return
    if battle["monster_hp"] <= 0:
        coin_gain = battle["monster_coins"]
        exp_gain = random.randint(10, 20)
        char.coins += coin_gain
        leveled = char.gain_exp(exp_gain)
        text += f"\n🏆 {battle['monster_name']} повержен! Получено {exp_gain} опыта и {coin_gain} монет."
        if leveled:
            text += f"\n🎉 Уровень повышен до {char.level}!"
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

@dp.message_handler(commands=['magic'])
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
    text = f"🔮 Ты атаковал магией {battle['monster_name']} на {damage} урона (HP монстра: {battle['monster_hp']})"
    if curse_damage > 0:
        text += f"\nКольцо ранит тебя на {curse_damage} HP."
        if not char.is_alive():
            text += "\n💀 Кольцо убило тебя!"
            del char._battle
            await message.reply(text)
            return
    if battle["monster_hp"] <= 0:
        coin_gain = battle["monster_coins"]
        exp_gain = random.randint(10, 20)
        char.coins += coin_gain
        leveled = char.gain_exp(exp_gain)
        text += f"\n🏆 {battle['monster_name']} повержен! Получено {exp_gain} опыта и {coin_gain} монет."
        if leveled:
            text += f"\n🎉 Уровень повышен до {char.level}!"
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
    text = "🛡️ Ты встал в защиту!"
    if curse_damage > 0:
        text += f"\nКольцо ранит тебя на {curse_damage} HP."
        if not char.is_alive():
            text += "\n💀 Кольцо убило тебя!"
            del char._battle
            await message.reply(text)
            return
    enemy_damage = random.randint(5, battle["monster_damage"])
    reduction = char.agility // 2
    actual_damage = max(1, enemy_damage - reduction)
    char.hp -= actual_damage
    text += f"\n{battle['monster_name']} атаковал на {actual_damage} HP (защита снизила урон)."
    if not char.is_alive():
        text += "\n💀 Ты погиб в бою!"
        del char._battle
    else:
        text += f"\nТвое HP: {char.hp}/{char.max_hp}"
    await message.reply(text)

@dp.message_handler(commands=['shop'])
async def shop(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message