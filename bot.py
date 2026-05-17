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
                           "Используй /help для списка команд")
    else:
        await message.reply("Ты уже в игре! Используй /help")

async def help_command(message: types.Message):
    help_text = (
        "📜 Команды Уроборос:\n"
        "/start - начать игру\n"
        "/status - характеристики\n"
        "/inventory - инвентарь\n"
        "/use <предмет> - использовать предмет\n"
        "/shop - магазин\n"
        "/buy <предмет> - купить предмет\n"
        "/battle - сразиться с монстром\n"
        "/travel - отправиться в путешествие\n"
        "/curse - проверить уровень проклятия"
    )
    await message.reply(help_text)

async def status_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    status_text = (
        f"🛡️ Уровень: {char.level}\n"
        f"❤️ HP: {char.hp}/{char.max_hp}\n"
        f"💪 Сила: {char.strength}\n"
        f"🏃 Ловкость: {char.agility}\n"
        f"🔮 Магия: {char.magic}\n"
        f"🪙 Монеты: {char.coins}\n"
        f"☠️ Проклятие: {char.curse}\n"
        f"📍 Локация: {char.location}\n"
        f"✨ Опыт: {char.exp}/{char.exp_to_next}"
    )
    await message.reply(status_text)

async def inventory_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    if not char.inventory:
        await message.reply("🎒 Инвентарь пуст")
    else:
        items_list = "\n".join([f"- {item}" for item in char.inventory])
        await message.reply(f"🎒 Инвентарь:\n{items_list}")

async def use_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    try:
        item_name = message.get_args()
        if not item_name:
            await message.reply("Укажи предмет: /use <предмет>")
            return
        result = char.use_item(item_name)
        await message.reply(result)
    except Exception as e:
        await message.reply(f"Ошибка при использовании предмета: {e}")

async def shop_command(message: types.Message):
    shop_items = {
        "зелье здоровья": 15,
        "эликсир силы": 25,
        "зелье магии": 25,
        "свиток защиты": 30,
        "зелье лечения": 50
    }
    shop_text = "🏪 Магазин:\n"
    for item, price in shop_items.items():
        shop_text += f"- {item}: {price} монет\n"
    shop_text += "\nКупить: /buy <предмет>"
    await message.reply(shop_text)

async def buy_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    shop_items = {
        "зелье здоровья": 15,
        "эликсир силы": 25,
        "зелье магии": 25,
        "свиток защиты": 30,
        "зелье лечения": 50
    }
    try:
        item_name = message.get_args()
        if not item_name:
            await message.reply("Укажи предмет: /buy <предмет>")
            return
        if item_name not in shop_items:
            await message.reply(f"Нет такого предмета в магазине")
            return
        price = shop_items[item_name]
        if char.coins < price:
            await message.reply(f"Недостаточно монет. Нужно: {price}, у тебя: {char.coins}")
            return
        char.coins -= price
        char.inventory.append(item_name)
        await message.reply(f"✅ Ты купил {item_name} за {price} монет")
    except Exception as e:
        await message.reply(f"Ошибка при покупке: {e}")

async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    if not char.is_alive():
        await message.reply("Ты мёртв! Начни заново через /start")
        return
    
    monster_hp = random.randint(20, 50)
    monster_damage = random.randint(3, 10)
    monster_name = random.choice(["Гоблин", "Скелет", "Волк", "Паук"])
    
    battle_log = f"⚔️ Бой с {monster_name}!\n"
    battle_log += f"У монстра {monster_hp} HP, урон {monster_damage}\n\n"
    
    turn = 1
    while monster_hp > 0 and char.is_alive():
        curse_damage = char.curse_effect()
        if curse_damage > 0:
            battle_log += f"☠️ Проклятие наносит {curse_damage} урона\n"
        if not char.is_alive():
            break
        
        battle_log += f"\n--- Ход {turn} ---\n"
        choose_msg = await message.reply("1 - Атака / 2 - Магия / 3 - Защита")
        
        try:
            player_action = message.get_args()
            if player_action == "1":
                damage = char.attack_physical()
                monster_hp -= damage
                battle_log += f"Ты атаковал и нанёс {damage} урона\n"
            elif player_action == "2":
                damage = char.attack_magical()
                monster_hp -= damage
                battle_log += f"Ты использовал магию и нанёс {damage} урона\n"
            elif player_action == "3":
                damage_taken = char.defend(monster_damage)
                battle_log += f"Ты защищаешься, получая {damage_taken} урона\n"
            else:
                damage = char.attack_physical()
                monster_hp -= damage
                battle_log += f"Ты атаковал и нанёс {damage} урона\n"
        except Exception as e:
            battle_log += f"Ты атаковал\n"
            damage = char.attack_physical()
            monster_hp = max(0, monster_hp - damage)
        
        if monster_hp > 0:
            monster_attack = random.randint(1, monster_damage)
            char.hp -= monster_attack
            battle_log += f"Монстр атакует и наносит {monster_attack} урона\n"
        
        turn += 1
        
        if turn > 20:
            break
    
    if monster_hp <= 0:
        exp_gained = random.randint(5, 15)
        coins_gained = random.randint(3, 8)
        char.gain_exp(exp_gained)
        char.coins += coins_gained
        battle_log += f"\n🎉 Победа! Ты получил {exp_gained} опыта и {coins_gained} монет"
        if random.random() < 0.2:
            loot = random.choice(["зелье здоровья", "эликсир силы", "свиток защиты"])
            char.inventory.append(loot)
            battle_log += f"\n🎁 Ты нашёл {loot}!"
    elif not char.is_alive():
        battle_log += f"\n💀 Ты погиб в бою! Начни заново через /start"
        del characters[user_id]
    
    await message.reply(battle_log)

async def travel(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    
    events = [
        {"name": "нападение разбойников", "type": "enemy", "damage": random.randint(5, 15)},
        {"name": "заброшенный сундук", "type": "loot", "coins": random.randint(5, 20)},
        {"name": "старый мудрец", "type": "exp", "exp": random.randint(10, 25)},
        {"name": "проклятое болото", "type": "curse", "curse_increase": random.randint(1, 3)},
        {"name": "торговец на дороге", "type": "shop"},
        {"name": "привал у костра", "type": "heal", "heal": random.randint(10, 30)},
        {"name": "загадочный артефакт", "type": "item", "item": random.choice(["зелье здоровья", "эликсир силы", "зелье магии"])},
        {"name": "ловушка", "type": "trap", "damage": random.randint(8, 20)},
    ]
    
    event = random.choice(events)
    travel_log = f"🚶 Ты отправился в путешествие из {char.location}...\n\n"
    
    try:
        if event["type"] == "enemy":
            damage = event["damage"]
            char.hp -= damage
            travel_log += f"⚠️ {event['name']}! Ты получаешь {damage} урона"
            if not char.is_alive():
                travel_log += "\n💀 Ты погиб в дороге! Начни через /start"
                del characters[user_id]
        elif event["type"] == "loot":
            coins = event["coins"]
            char.coins += coins
            travel_log += f"💰 {event['name']}! Ты находишь {coins} монет"
        elif event["type"] == "exp":
            exp = event["exp"]
            leveled_up = char.gain_exp(exp)
            travel_log += f"📚 {event['name']}! Ты получаешь {exp} опыта"
            if leveled_up:
                travel_log += f"\n🎉 Уровень повышен! Ты теперь {char.level} уровня!"
        elif event["type"] == "curse":
            curse_increase = event["curse_increase"]
            char.curse += curse_increase
            travel_log += f"☠️ {event['name']}! Проклятие увеличилось на {curse_increase}"
        elif event["type"] == "shop":
            travel_log += f"🏪 {event['name']}! Используй /shop для покупки"
        elif event["type"] == "heal":
            heal = event["heal"]
            char.heal(heal)
            travel_log += f"🔥 {event['name']}! Ты восстановил {heal} HP"
        elif event["type"] == "item":
            item = event["item"]
            char.inventory.append(item)
            travel_log += f"✨ {event['name']}! Ты получил {item}"
        elif event["type"] == "trap":
            damage = event["damage"]
            char.hp -= damage
            travel_log += f"🕳️ {event['name']}! Ты получаешь {damage} урона"
            if not char.is_alive():
                travel_log += "\n💀 Ты погиб в ловушке! Начни через /start"
                del characters[user_id]
        
        if char.is_alive():
            old_location = char.location
            new_location = random.choice(["таверна", "лес", "горы", "болото", "деревня", "пещера"])
            char.location = new_location
            travel_log += f"\n📍 Ты прибыл в {new_location}"
        
        curse_damage = char.curse_effect()
        if curse_damage > 0 and char.is_alive():
            travel_log += f"\n☠️ Кольцо пожирает тебя: -{curse_damage} HP"
            if not char.is_alive():
                travel_log += "\n💀 Кольцо пожрало твою душу! Начни заново через /start"
                del characters[user_id]
        
    except Exception as e:
        travel_log += f"\n❌ Произошла ошибка в путешествии: {e}"
    
    await message.reply(travel_log)

async def curse_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    char = characters[user_id]
    curse_text = f"☠️ Уровень проклятия: {char.curse}/10\n"
    if char.curse >= 10:
        curse_text += "⚠️ Кольцо вот-вот поглотит тебя!"
    elif char.curse >= 5:
        curse_text += "⚠️ Ты чувствуешь, как кольцо сжимается..."
    else:
        curse_text += "Пока всё спокойно..."
    curse_text += f"\n\nКаждое путешествие может усилить проклятие!"