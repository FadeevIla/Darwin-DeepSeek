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

characters = {}

async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        characters[user_id] = RPGCharacter(user_id)
        await message.reply("Добро пожаловать в Уроборос! Твой персонаж создан.\n"
                           "Используй /help для списка команд")
    else:
        await message.reply("Ты уже в игре! Используй /help для списка команд")

async def help_command(message: types.Message):
    help_text = (
        "🎮 Команды Уроборос:\n\n"
        "/start - Начать новую игру\n"
        "/help - Показать это сообщение\n"
        "/echo <текст> - Повторить текст\n"
        "/dice - Бросить кубик (1-6)\n"
        "/coinflip - Подбросить монетку\n\n"
        "⚔️ Боевая система:\n"
        "Сила - физическая атака\n"
        "Ловкость - защита\n"
        "Магия - магическая атака\n"
        "Проклятие - урон от кольца"
    )
    await message.reply(help_text)

async def echo(message: types.Message):
    text = message.get_args()
    if not text:
        await message.reply("Напиши текст после /echo")
        return
    await message.reply(text)

async def dice(message: types.Message):
    result = random.randint(1, 6)
    await message.reply(f"🎲 Ты бросил кубик и выпало: {result}")

async def coinflip(message: types.Message):
    result = random.choice(["Орёл", "Решка"])
    await message.reply(f"🪙 Монетка показала: {result}")

async def battle(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала начни игру через /start")
        return
    
    char = characters[user_id]
    if not char.is_alive():
        await message.reply("Ты мёртв! Начни заново через /start")
        return
    
    monster_hp = random.randint(30, 80)
    monster_strength = random.randint(5, 15)
    monster_magic = random.randint(3, 10)
    
    battle_log = f"⚔️ Бой начался!\n"
    battle_log += f"Ты: {char.hp}/{char.max_hp} HP | Монстр: {monster_hp} HP\n\n"
    
    while char.is_alive() and monster_hp > 0:
        player_choice = random.choice(["физическая", "магическая"])
        
        if player_choice == "физическая":
            damage = char.attack_physical()
            monster_hp -= damage
            battle_log += f"🗡️ Ты нанёс {damage} физического урона! (HP монстра: {monster_hp})\n"
        else:
            damage = char.attack_magical()
            monster_hp -= damage
            battle_log += f"🔮 Ты нанёс {damage} магического урона! (HP монстра: {monster_hp})\n"
        
        if monster_hp <= 0:
            exp_gain = random.randint(10, 30)
            coin_gain = random.randint(5, 20)
            char.gain_exp(exp_gain)
            char.coins += coin_gain
            battle_log += f"\n🎉 Ты победил! +{exp_gain} опыта, +{coin_gain} монет"
            break
        
        monster_choice = random.choice(["физическая", "магическая"])
        if monster_choice == "физическая":
            monster_damage = monster_strength + random.randint(0, 5)
        else:
            monster_damage = monster_magic + random.randint(0, 8)
        
        actual_damage = char.defend(monster_damage)
        battle_log += f"💥 Монстр нанёс {actual_damage} урона! (Твои HP: {char.hp})\n"
        
        if not char.is_alive():
            battle_log += "\n💀 Ты погиб в бою! Начни заново через /start"
            del characters[user_id]
            break
    
    await message.reply(battle_log)

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
    await message.reply(curse_text)

dp.register_message_handler(start, commands=['start'])
dp.register_message_handler(help_command, commands=['help'])
dp.register_message_handler(echo, commands=['echo'])
dp.register_message_handler(dice, commands=['dice'])
dp.register_message_handler(coinflip, commands=['coinflip'])
dp.register_message_handler(battle, commands=['battle'])
dp.register_message_handler(curse_command, commands=['curse'])

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)