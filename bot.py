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
            {"text": "Ты встретил старого мудреца на дороге. Он дал тебе 5 монет.", "coins": 5, "hp": 0, "curse": 0},
            {"text": "Ты нашёл сундук с сокровищами! +10 монет.", "coins": 10, "hp": 0, "curse": 0},
            {"text": "Ты провалился в яму! -10 HP.", "coins": 0, "hp": -10, "curse": 0},
            {"text": "Ты почувствовал, как кольцо сжалось на пальце. Проклятие усилилось!", "coins": 0, "hp": 0, "curse": 1},
            {"text": "Ты нашёл зелье здоровья.", "coins": 0, "hp": 0, "curse": 0, "item": "зелье здоровья"},
            {"text": "Ты встретил торговца, который продал тебе эликсир силы за 5 монет.", "coins": -5, "hp": 0, "curse": 0, "item": "эликсир силы", "cost": 5},
        ]
        event = random.choice(events)
        log = event["text"] + "\n"
        if event.get("coins", 0) != 0:
            self.coins += event["coins"]
            log += f"💰 Монет: {self.coins}\n"
        if event.get("hp", 0) != 0:
            self.hp += event["hp"]
            log += f"❤️ HP: {self.hp}/{self.max_hp}\n"
        if event.get("curse", 0) != 0:
            self.curse = min(10, self.curse + 1)
            log += f"☠️ Проклятие: {self.curse}/10\n"
        if event.get("item"):
            if event.get("cost", 0) <= self.coins:
                self.coins -= event["cost"]
                self.inventory.append(event["item"])
                log += f"📦 Получен предмет: {event['item']}\n"
            else:
                log += "🤷 Недостаточно монет для покупки.\n"
        return log

    def get_status(self):
        return f"Уровень: {self.level}\n❤️ HP: {self.hp}/{self.max_hp}\n💪 Сила: {self.strength}\n🏃 Ловкость: {self.agility}\n🔮 Магия: {self.magic}\n☠️ Проклятие: {self.curse}/10\n💰 Монет: {self.coins}\n📦 Инвентарь: {', '.join(self.inventory) if self.inventory else 'пусто'}"

players = {}

@dp.message_handler(commands=['start'])
async def start_game(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        players[user_id] = RPGCharacter(user_id)
    char = players[user_id]
    
    await message.reply(f"Добро пожаловать в Уроборос, {message.from_user.first_name}!\n"
                         f"Ты — искатель приключений, нашедший древнее кольцо.\n"
                         f"Оно даёт силу, но пожирает владельца.\n\n"
                         f"{char.get_status()}\n\n"
                         f"Команды:\n"
                         f"/status — текущее состояние\n"
                         f"/explore — отправиться в приключение\n"
                         f"/battle — найти врага и сразиться\n"
                         f"/inventory — посмотреть инвентарь\n"
                         f"/shop — магазин предметов\n"
                         f"/heal — использовать зелье здоровья")

@dp.message_handler(commands=['status'])
async def show_status(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    await message.reply(char.get_status())

@dp.message_handler(commands=['explore'])
async def explore(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    
    event_log = char.random_event()
    if char.hp <= 0:
        await message.reply("☠️ Ты погиб от ран во время путешествия. Игра окончена.")
        del players[user_id]
        return
    
    curse_damage = char.curse_effect()
    if curse_damage > 0:
        event_log += f"\n☠️ Кольцо пожирает тебя: -{curse_damage} HP"
    if char.hp <= 0:
        await message.reply("☠️ Кольцо высосало из тебя последние силы. Ты мёртв.")
        del players[user_id]
        return
    
    await message.reply(event_log)

@dp.message_handler(commands=['battle'])
async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    
    # Генерация врага
    enemy_hp = 20 + random.randint(0, 20) + char.level * 5
    enemy_max_hp = enemy_hp
    enemy_strength = 5 + random.randint(0, 5) + char.level * 2
    
    battle_log = f"⚔️ Ты встретил врага! HP: {enemy_hp}, Сила: {enemy_strength}\n\n"
    
    # Бой в 3 раунда
    for round_num in range(1, 4):
        battle_log += f"Раунд {round_num}:\n"
        
        # Ход игрока
        attack_choice = random.choice(["физическая", "магическая"])
        if attack_choice == "физическая":
            player_damage = char.attack_physical()
            enemy_hp -= player_damage
            battle_log += f"🗡️ Ты атакуешь физически и наносишь {player_damage} урона!\n"
        else:
            player_damage = char.attack_magical()
            enemy_hp -= player_damage
            battle_log += f"🔮 Ты используешь магию и наносишь {player_damage} урона!\n"
        
        if enemy_hp <= 0:
            battle_log += f"💀 Враг повержен!\n"
            break
        
        # Ход врага
        enemy_damage = random.randint(0, enemy_strength)
        actual_damage = char.defend(enemy_damage)
        battle_log += f"👊 Враг атакует и наносит {actual_damage} урона!\n"
        
        if not char.is_alive():
            battle_log += "☠️ Ты погиб в бою!\n"
            await message.reply(battle_log + "\n💀 Игра окончена.")
            del players[user_id]
            return
        
        # Проклятие действует каждый раунд
        curse_damage = char.curse_effect()
        if curse_damage > 0:
            battle_log += f"☠️ Кольцо пожирает тебя: -{curse_damage} HP\n"
        if not char.is_alive():
            battle_log += "☠️ Кольцо высосало из тебя последние силы!\n"
            await message.reply(battle_log + "\n💀 Игра окончена.")
            del players[user_id]
            return
        
        battle_log += f"❤️ Твоё HP: {char.hp}/{char.max_hp} | 💀 Враг: {enemy_hp}/{enemy_max_hp}\n\n"
    
    # Результат боя
    if enemy_hp <= 0:
        exp_reward = 10 + random.randint(0, 10) + char.level * 2
        coin_reward = 5 + random.randint(0, 10) + char.level * 2
        char.coins += coin_reward
        battle_log += f"\n🎉 Победа! Ты получил {exp_reward} опыта и {coin_reward} монет!"
        
        if char.gain_exp(exp_reward):
            battle_log += f"\n🎉 Поздравляю! Ты достиг уровня {char.level}! Все характеристики +1, HP увеличено!"
        
        if random.randint(1, 5) == 1:
            char.curse = min(10, char.curse + 1)
            battle_log += f"\n☠️ Проклятие усилилось до {char.curse}/10!"
        
        if random.randint(1, 3) == 1:
            items = ["зелье здоровья", "эликсир силы", "зелье магии"]
            item = random.choice(items)
            char.inventory.append(item)
            battle_log += f"\n📦 Ты нашёл {item}!"
    else:
        battle_log += "\n💀 Ты погиб! Игра окончена."
        await message.reply(battle_log)
        del players[user_id]
        return
    
    await message.reply(battle_log)

@dp.message_handler(commands=['inventory'])
async def show_inventory(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    
    if not char.inventory:
        await message.reply("📦 Твой инвентарь пуст.")
    else:
        inv_text = "📦 Твой инвентарь:\n" + "\n".join([f"• {item}" for item in set(char.inventory)])
        await message.reply(inv_text)

@dp.message_handler(commands=['shop'])
async def shop(message: types.Message):
    user_id = message.from_user.id
    if user_id not in players:
        await message.reply("Сначала начни игру через /start")
        return
    char = players[user_id]
    
    items = [
        ("зелье здоровья", 5, "Восстанавливает 30 HP"),
        ("эликсир силы", 8, "Увеличивает силу на 2"),
        ("зелье магии", 8, "Увеличивает магию на 2"),
        ("зелье ловкости", 8, "Увеличивает ловкость на 2"),
    ]
    
    shop_text = "🏪 Магазин:\n"
    for i, (name, price, desc) in enumerate(items, 1):
        shop_text += f"{i}. {name} — {price} монет — {desc}\n"
    shop_text += f"\n💰 У тебя: {char.coins} монет"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for i, (name, price, desc) in enumerate(items, 1):
        if char.coins >= price:
            keyboard.add(types.InlineKeyboardButton(f"Купить {name} ({price})", callback_data=f"buy_{name}"))
    
    await message.reply(shop_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def process_buy(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in players:
        await callback_query.message.reply("Сначала начни игру через /start")
        await callback_query.answer()
        return
    
    char = players[user_id]
    item_name = callback_query.data[4:]
    
    prices = {"зелье здоровья": 5, "эликсир силы": 8, "зелье магии": 8, "зелье ловкости": 8}
    price = prices.get(item_name, 5)
    
    if char.buy_item(item_name, price):
        if item_name == "зелье ловкости":
            char.agility += 2
        await callback_query.message.reply(f"✅ Ты купил {item_name} за {price} монет!")
    else:
        await callback_query.message.reply("❌ У тебя недостаточно монет!")
    
    await callback_query.answer()

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

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)