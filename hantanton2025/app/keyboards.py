from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Стандартная викторина")],
                                     [KeyboardButton(text="Банк вопросов")],
                                     [KeyboardButton(text="Таблица лидеров")]])

answer1 = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="1", callback_data="1")],
                                               [InlineKeyboardButton(text="2", callback_data="2")],
                                               [InlineKeyboardButton(text="3", callback_data="3")]])




following = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="следующий вопрос", callback_data="next")],
                                                  [InlineKeyboardButton(text="конец игры", callback_data="stop")]])
