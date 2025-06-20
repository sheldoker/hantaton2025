from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Основная клавиатура
main = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="Стандартная викторина")],
    [KeyboardButton(text="Создать дуэль")],
    [KeyboardButton(text="Присоединиться к дуэли")],
    [KeyboardButton(text="Банк вопросов")],
    [KeyboardButton(text="Таблица лидеров")]
])

# Клавиатура с вариантами ответов
answer1 = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="1", callback_data="1")],
    [InlineKeyboardButton(text="2", callback_data="2")],
    [InlineKeyboardButton(text="3", callback_data="3")]
])

# Следующая/Закончить игру
following = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Следующий вопрос", callback_data="next")],
    [InlineKeyboardButton(text="Завершить игру", callback_data="stop")]
])


