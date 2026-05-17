import random
from aiogram import types
from core import feedback

@dp.message_handler(commands=['report'])
async def report_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id != 6909561387:
        await message.reply("⛔ Эта команда только для администратора.")
        return
    text = message.get_args()
    if not text:
        await message.reply("📝 Использование: /report <текст сообщения>\nНапиши баг или пожелание.")
        return
    try:
        feedback.add_feedback(user_id, text)
        await message.reply("✅ Сообщение отправлено разработчику. Спасибо!")
    except Exception as e:
        logger.error(f"Ошибка при сохранении фидбека от {user_id}: {e}")
        await message.reply("❌ Не удалось отправить сообщение. Попробуй позже.")