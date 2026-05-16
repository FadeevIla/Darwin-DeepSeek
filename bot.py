from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from core import environ_map, update_notifier
from datetime import datetime, timedelta
import secrets
import asyncio
import random
import logging
import aiohttp
import os

logger = logging.getLogger(__name__)
BOT_TOKEN = environ_map['TELEGRAM_BOT_TOKEN']

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

async def start(message: types.Message):
    await message.reply("Привет, я бот!")

async def help_command(message: types.Message):
    await message.reply('Список команд: /start, /help, /about, /status, /joke, /fact, /quote, /weather, /stats, /poll, /remind, /info, /whatsnew, /horoscope, /random, /timer, /suggest, /coinflip, /echo, /dice, /remindme, /giveaway')

async def about(message: types.Message):
    await message.reply('Это бот, который может ответить на различные вопросы.')

async def status(message: types.Message):
    await message.reply('Бот работает!')

async def joke(message: types.Message):
    jokes = [
        'Почему компьютер шел в гимнастку? Чтобы улучшить свою скорость!',
        'Почему программист не любит воду? Потому что он боится "отплывать"!',
        'Почему компьютер не может ходить в кино? Потому что он не может купить билет!'
    ]
    await message.reply(random.choice(jokes))

async def fact(message: types.Message):
    facts = [
        'Солнце весит 330 000 масс-сон, что примерно в 330 000 раз больше, чем Земля.',
        'Самая большая планета в нашей солнечной системе - Юпитер.',
        'Самая дальняя планета от Солнца - Плутон.'
    ]
    await message.reply(random.choice(facts))

async def quote(message: types.Message):
    quotes = [
        'Всегда помните, что жизнь коротка, но воспоминания о ней могут быть вечными.',
        'Никогда не сдавайтесь, потому что победа всегда впереди.',
        'Всегда следуйте своему сердцу, потому что оно знает, что правильно.'
    ]
    await message.reply(random.choice(quotes))

async def weather(message: types.Message):
    if 'OPENWEATHERMAP_API_KEY' not in os.environ:
        await message.reply('Пожалуйста, добавьте ключ OPENWEATHERMAP_API_KEY в переменные окружения.')
        return
    try:
        city = message.text.split()[1]
        api_key = os.environ['OPENWEATHERMAP_API_KEY']
        url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    weather_description = data['weather'][0]['description']
                    await message.reply(f'Погода в {city}: {weather_description}')
                else:
                    await message.reply('Ошибка. Проверьте город или ключ от API.')
    except Exception as e:
        logger.error(f'Ошибка при получении погоды: {e}')
        await message.reply('Ошибка при получении погоды.')

async def echo(message: types.Message):
    text = message.get_args()
    if text:
        await message.reply(f'Вы написали: {text}')
    else:
        await message.reply('Введите текст после команды /echo')

async def stats(message: types.Message):
    await message.reply('Статистика пока недоступна.')

async def poll(message: types.Message):
    await message.reply('Голосование пока не реализовано.')

async def remind(message: types.Message):
    await message.reply('Напомните мне через 10 секунд!')

async def info(message: types.Message):
    await message.reply('Информация о боте.')

async def whatsnew(message: types.Message):
    await message.reply('Новое: добавлены команды /giveaway и /remindme.')

async def remind_me(message: types.Message):
    await message.reply('Напоминалка установлена!')

async def horoscope(message: types.Message):
    signs = ['Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева', 'Весы', 'Скорпион', 'Стрелец', 'Козерог', 'Водолей', 'Рыбы']
    sign = random.choice(signs)
    await message.reply(f'Гороскоп для {sign}: Сегодня удачный день!')

async def random_command(message: types.Message):
    number = random.randint(1, 100)
    await message.reply(f'Случайное число: {number}')

async def timer(message: types.Message):
    from aiogram.types import ReplyKeyboardRemove
    await message.reply('Таймер запущен на 5 секунд!')
    await asyncio.sleep(5)
    await message.reply('Время вышло!')

async def suggest(message: types.Message):
    suggestions = ['Попробуй /coinflip', 'Попробуй /dice', 'Попробуй /joke']
    await message.reply(random.choice(suggestions))

async def coinflip(message: types.Message):
    result = random.choice(['Орел', 'Решка'])
    await message.reply(f'Монетка: {result}')

async def dice(message: types.Message):
    result = random.randint(1, 6)
    await message.reply(f'Кубик показал: {result}')

async def giveaway(message: types.Message):
    await message.reply('Розыгрыш! Напишите /giveaway, чтобы принять участие!')

async def support(message: types.Message):
    await message.reply('Если у вас возникли вопросы, напишите @support_username')

dp.register_message_handler(start, commands=['start'])
dp.register_message_handler(help_command, commands=['help'])
dp.register_message_handler(about, commands=['about'])
dp.register_message_handler(status, commands=['status'])
dp.register_message_handler(joke, commands=['joke'])
dp.register_message_handler(fact, commands=['fact'])
dp.register_message_handler(quote, commands=['quote'])
dp.register_message_handler(weather, commands=['weather'])
dp.register_message_handler(echo, commands=['echo'])
dp.register_message_handler(stats, commands=['stats'])
dp.register_message_handler(poll, commands=['poll'])
dp.register_message_handler(remind, commands=['remind'])
dp.register_message_handler(info, commands=['info'])
dp.register_message_handler(whatsnew, commands=['whatsnew'])
dp.register_message_handler(remind_me, commands=['remindme'])
dp.register_message_handler(horoscope, commands=['horoscope'])
dp.register_message_handler(random_command, commands=['random'])
dp.register_message_handler(timer, commands=['timer'])
dp.register_message_handler(suggest, commands=['suggest'])
dp.register_message_handler(coinflip, commands=['coinflip'])
dp.register_message_handler(dice, commands=['dice'])
dp.register_message_handler(giveaway, commands=['giveaway'])
dp.register_message_handler(support, commands=['support'])

if __name__ == '__main__':
    executor.start_polling(dp)