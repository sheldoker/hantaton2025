from aiogram import Bot, Dispatcher, F, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.command import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from app import handlers1


# Токен вашего бота
token = "7788995505:AAH6E-zroA51pTjBymtc8WSAq3aH-1_AuAQ"

# Создание экземпляра бота и маршрутизатора
bot = Bot(token=token)
dp = Dispatcher()

# Регистрируем обработчики из router.py
dp.include_router(handlers1.router)


# Запуск бота
if __name__ == "__main__":
    dp.run_polling(bot)