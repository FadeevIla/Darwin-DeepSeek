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
    await message.reply('Список команд: /start, /help, /about, /status, /joke, /fact, /quote, /weather, /stats, /poll, /remind, /info, /whatsnew, /horoscope, /random, /timer, /suggest, /coinflip, /echo, /dice, /remindme, /giveaway, /ping')

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
        logger.error(f'Ошибка получения погоды: {e}')
        await message.reply('Произошла ошибка при получении погоды.')

async def echo(message: types.Message):
    await message.reply(message.text)

async def stats(message: types.Message):
    await message.reply('Статистика бота: пока не реализована.')

async def poll(message: types.Message):
    await message.reply('Функция опроса пока не реализована.')

async def remind(message: types.Message):
    await message.reply('Функция напоминания пока не реализована.')

async def info(message: types.Message):
    await message.reply('Информация о боте: версия 1.0')

async def whatsnew(message: types.Message):
    await message.reply('Что нового: добавлены новые команды.')

async def remind_me(message: types.Message):
    await message.reply('Функция напоминания пока не реализована.')

async def horoscope(message: types.Message):
    await message.reply('Гороскоп пока не реализован.')

async def random_command(message: types.Message):
    await message.reply(str(random.randint(1, 100)))

async def timer(message: types.Message):
    await message.reply('Таймер пока не реализован.')

async def suggest(message: types.Message):
    await message.reply('Предложение: попробуйте команду /joke')

async def coinflip(message: types.Message):
    result = random.choice(['Орёл', 'Решка'])
    await message.reply(result)

async def dice(message: types.Message):
    result = random.randint(1, 6)
    await message.reply(str(result))

async def giveaway(message: types.Message):
    await message.reply('Розыгрыш пока не проводится.')

async def support(message: types.Message):
    await message.reply('Поддержка: напишите @admin')

async def ping(message: types.Message):
    await message.reply('Понг!')

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
dp.register_message_handler(ping, commands=['ping'])

if __name__ == '__main__':
    executor.start_polling(dp)