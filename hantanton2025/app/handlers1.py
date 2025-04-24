from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random
import app.keyboards as kb
from aiogram.types import InputMediaPhoto
import json

router = Router()

# Загрузим вопросы из JSON-файла
with open('app/questions.json', encoding='utf-8') as f:
    questions = json.load(f)

# Фунции для работы с результатами
def load_scores(filename='scores.json'):
    """Загружает существующие результаты."""
    try:
        with open(filename, 'r') as file:
            scores = json.load(file)
    except FileNotFoundError:
        scores = []
    return scores

def save_scores(scores, filename='scores.json'):
    """Сохраняет результаты обратно в JSON-файл."""
    with open(filename, 'w') as file:
        json.dump(scores, file)

def generate_leaderboard():
    """Генерирует таблицу лидеров."""
    scores = load_scores()
    sorted_scores = sorted(scores, key=lambda x: x['score'], reverse=True)
    top_players = sorted_scores[:10]  # Берём только 10 лучших игроков
    return top_players

# Стейт-группа для управления игрой
class GameState(StatesGroup):
    WAITING_FOR_ANSWER = State()

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Добро пожаловать в бота для Хантантона! Выберите режим игры:", reply_markup=kb.main)

# Функция отправки вопроса
async def ask_question(message: Message, state: FSMContext):
    data = await state.get_data()
    if 'question' in data:
        current_question = data['question']
        text = f"{current_question['question']}\n"
        for i, option in enumerate(current_question['options'], start=1):
            text += f"{i}. {option}\n"

        # Определяем способ отправки вопроса в зависимости от наличия изображения
        if current_question['image_url']:
            # Если есть изображение, отправляем сообщение с фотографией и подписью
            await message.answer_photo(
                photo=current_question['image_url'],
                caption=text,
                reply_markup=kb.answer1
            )
        else:
            # Если изображения нет, отправляем простой текст
            await message.answer(
                text=text,
                reply_markup=kb.answer1
            )

# Загрузка первого вопроса
@router.message(F.text == "Стандартная викторина")
async def quiz_start(message: Message, state: FSMContext):
    unused_questions = questions.copy()  # Создаем копию всех вопросов
    first_question = random.choice(unused_questions)
    unused_questions.remove(first_question)  # Убираем первый выбранный вопрос из списка неиспользованных
    await state.update_data(question=first_question, score=0, unused_questions=unused_questions)
    await ask_question(message, state)
    await state.set_state(GameState.WAITING_FOR_ANSWER)

# Универсальная функция для обновления результатов
async def update_result_message(bot: Bot, callback_query: CallbackQuery, result_message: str):
    original_message = callback_query.message
    has_caption = bool(original_message.caption)  # Проверка наличия подписи в оригинальном сообщении
    
    if has_caption:
        # Редактируем подпись (если была исходная подпись)
        await bot.edit_message_caption(
            chat_id=original_message.chat.id,
            message_id=original_message.message_id,
            caption=result_message,
            reply_markup=kb.following
        )
    else:
        # Просто обновляем текст сообщения
        await bot.edit_message_text(
            chat_id=original_message.chat.id,
            message_id=original_message.message_id,
            text=result_message,
            reply_markup=kb.following
        )

# Обработка нажатий кнопок
@router.callback_query(lambda c: True)
async def process_answer(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    action = callback_query.data
    data = await state.get_data()

    if action.isdigit():  # Пользователь выбрал номер варианта ответа
        answer_number = int(action) - 1  # Перевод номера кнопки в индекс массива вариантов
        current_question = data['question']
        selected_option = current_question['options'][answer_number]
        correct_answer = current_question['answer']

        result_message = ""
        if selected_option == correct_answer:
            current_data = await state.get_data()
            new_score = current_data.get('score', 0) + 1
            await state.update_data(score=new_score)
            result_message = f"ПРАВИЛЬНО! Ваш счёт: {new_score}"
        else:
            result_message = f"НЕПРАВИЛЬНО. Правильный ответ: {correct_answer}"

        # Обновляем результат на экране
        await update_result_message(bot, callback_query, result_message)

    elif action == "next":  # Кнопка "Следующий вопрос"
        unused_questions = data.get('unused_questions')
        if not unused_questions:
            await state.clear()
            await bot.send_message(chat_id=callback_query.from_user.id, text="Вопросы закончились!")
            return
        
        next_question = random.choice(unused_questions)
        unused_questions.remove(next_question)  # Удаляем этот вопрос из оставшихся
        await state.update_data(question=next_question, unused_questions=unused_questions)
        await ask_question(callback_query.message, state)

    elif action == "stop":  # Завершение игры
        final_score = data.get("score", 0)
        user_id = callback_query.from_user.id
        username = callback_query.from_user.username or callback_query.from_user.first_name
        scores = load_scores()
        scores.append({"user_id": user_id, "username": username, "score": final_score})
        save_scores(scores)
        await state.clear()
        await bot.send_message(chat_id=callback_query.from_user.id, text=f"Игра закончена. Итоговый счёт: {final_score}")

# Команда для показа таблицы лидеров
@router.message(F.text == "Таблица лидеров")
async def show_leaderboard(message: Message):
    leaders = generate_leaderboard()
    if leaders:
        table = "\n".join([
            f"{i+1}. {leader['username']}: {leader['score']} очков"
            for i, leader in enumerate(leaders)
        ])
        await message.answer(f"Таблица лидеров:\n{table}")
    else:
        await message.answer("Пока никто не сыграл.")

# Показ полного банка вопросов
@router.message(F.text == "Банк вопросов")
async def show_full_question_bank(message: Message):
    media = []
    texts = []
    
    for idx, question in enumerate(questions):
        # Формируем текстовую версию вопроса
        texts.append(f"{idx+1}. Вопрос: {question['question']}, Варианты ответов: {' '.join(question['options'])}, Правильный ответ: {question['answer']}")
        
        # Добавляем изображение только если оно указано
        if question.get("image_url"):
            media.append(InputMediaPhoto(media=question["image_url"], caption=""))
    
    # Пошаговая отправка медиа-контента
    chunk_size = 10
    chunks = [media[i:i + chunk_size] for i in range(0, len(media), chunk_size)]
    
    for chunk in chunks:
        await message.answer_media_group(media=chunk)
    
    # Отдельно отправляем тексты вопросов
    for text in texts:
        await message.answer(text)