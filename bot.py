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
                       "/start - Начать игру\n"
                       "/help - Показать это сообщение\n"
                       "/echo <текст> - Повторить текст\n"
                       "/dice - Бросить кубик\n"
                       "/coinflip - Подбросить монетку\n"
                       "/battle - Сразиться с монстром\n"
                       "/status - Показать характеристики\n"
                       "/inventory - Показать инвентарь\n"
                       "/use <предмет> - Использовать предмет\n"
                       "/shop - Магазин\n"
                       "/buy <предмет> - Купить предмет")

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

    player = characters[user_id]
    monster = RPGCharacter(0)
    monster.hp = 50 + random.randint(0, 30)
    monster.max_hp = monster.hp
    monster.strength = random.randint(3, 10)
    monster.agility = random.randint(3, 10)
    monster.magic = random.randint(3, 10)

    battle_log = [f"⚔️ Бой с монстром (HP: {monster.hp})"]
    turn = 1

    while player.is_alive() and monster.is_alive():
        battle_log.append(f"\n--- Ход {turn} ---")

        curse_damage = player.curse_effect()
        if curse_damage > 0:
            battle_log.append(f"☠️ Проклятие наносит {curse_damage} урона (HP: {player.hp})")

        if not player.is_alive():
            battle_log.append("\n💀 Ты проиграл...")
            break

        player_attack_type = random.choice(["physical", "magical"])
        if player_attack_type == "physical":
            damage = player.attack_physical()
            actual_damage = monster.defend(damage)
            battle_log.append(f"🗡️ Ты нанёс {actual_damage} физического урона (HP монстра: {max(0, monster.hp)})")
        else:
            damage = player.attack_magical()
            actual_damage = monster.defend(damage)
            battle_log.append(f"🔮 Ты нанёс {actual_damage} магического урона (HP монстра: {max(0, monster.hp)})")

        if not monster.is_alive():
            coins_reward = random.randint(5, 15)
            exp_reward = random.randint(10, 25)
            player.coins += coins_reward
            leveled_up = player.gain_exp(exp_reward)
            battle_log.append(f"\n🎉 Ты победил! Получено {coins_reward} монет и {exp_reward} опыта")
            if leveled_up:
                battle_log.append(f"🌟 Уровень повышен! Теперь ты {player.level} уровня")
            break

        monster_attack_type = random.choice(["physical", "magical"])
        if monster_attack_type == "physical":
            damage = monster.attack_physical()
            actual_damage = player.defend(damage)
            battle_log.append(f"💥 Монстр нанёс {actual_damage} физического урона (твоё HP: {player.hp})")
        else:
            damage = monster.attack_magical()
            actual_damage = player.defend(damage)
            battle_log.append(f"💫 Монстр нанёс {actual_damage} магического урона (твоё HP: {player.hp})")

        turn += 1
        if turn > 20:
            battle_log.append("\n⏰ Бой затянулся... Ничья!")
            break

    player.hp = max(1, player.hp)
    await message.reply("\n".join(battle_log))

async def status_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return

    char = characters[user_id]
    status_text = (f"📊 Статус персонажа:\n"
                  f"Уровень: {char.level}\n"
                  f"Опыт: {char.exp}/{char.exp_to_next}\n"
                  f"HP: {char.hp}/{char.max_hp}\n"
                  f"Сила: {char.strength}\n"
                  f"Ловкость: {char.agility}\n"
                  f"Магия: {char.magic}\n"
                  f"Проклятие: {char.curse}\n"
                  f"Монеты: {char.coins}")
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
        items = "\n".join(f"• {item}" for item in char.inventory)
        await message.reply(f"🎒 Инвентарь:\n{items}")

async def use_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return

    item_name = message.get_args()
    if not item_name:
        await message.reply("Укажи предмет для использования. Пример: /use зелье здоровья")
        return

    result = characters[user_id].use_item(item_name)
    await message.reply(result)

async def shop_command(message: types.Message):
    await message.reply("🏪 Магазин:\n"
                       "• зелье здоровья - 15 монет (восстанавливает 30 HP)\n"
                       "• эликсир силы - 25 монет (Сила +2)\n"
                       "• зелье магии - 25 монет (Магия +2)\n"
                       "Используй /buy <предмет> для покупки")

async def buy_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in characters:
        await message.reply("Сначала создай персонажа через /start")
        return

    char = characters[user_id]
    item_name = message.get_args()

    if not item_name:
        await message.reply("Укажи предмет для покупки. Пример: /buy зелье здоровья")
        return

    prices = {
        "зелье здоровья": 15,
        "эликсир силы": 25,
        "зелье магии": 25
    }

    if item_name not in prices:
        await message.reply(f"Товар '{item_name}' не найден в магазине")
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