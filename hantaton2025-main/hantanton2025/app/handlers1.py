from aiogram import F, Router, Bot, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import random
import app.keyboards as kb
from aiogram.types import InputMediaPhoto, InputMedia
import json
import asyncio

# Настройка бота
bot = Bot(token="7788995505:AAH6E-zroA51pTjBymtc8WSAq3aH-1_AuAQ")  # ВАЖНО: укажите реальный токен вашего бота здесь!

router = Router()

# Словарь для хранения текущих активированных дуэлей
active_duels = {}

# Загрузка вопросов из файла
with open('app/questions.json', encoding='utf-8') as f:
    questions = json.load(f)

# Словарь для хранения вопросов с изображениями
questions_with_images = [q for q in questions if 'image_url' in q]

# Вспомогательная функция загрузки предыдущих результатов
def load_scores(filename='scores.json'):
    try:
        with open(filename, 'r') as file:
            scores = json.load(file)
    except FileNotFoundError:
        scores = []
    return scores

# Функция сохранения результатов в файл
def save_scores(username: str, score: int, filename='scores.json'):
    existing_scores = load_scores(filename)
    new_entry = {"username": username, "score": score}
    existing_scores.append(new_entry)
    with open(filename, 'w') as file:
        json.dump(existing_scores, file, indent=4)

# Функция формирования таблицы лидеров
def generate_leaderboard():
    scores = load_scores()
    sorted_scores = sorted(scores, key=lambda x: x['score'], reverse=True)
    top_players = sorted_scores[:5]
    return top_players

# Класс состояний для обычных игровых сессий
class GameState(StatesGroup):
    WAITING_FOR_ANSWER = State()

# Класс состояний для дуэлей
class Duels(StatesGroup):
    WAITING_FOR_CODE_INPUT = State()  # Ожидание ввода кода дуэли
    READY_TO_DUEL = State()           # Готовность к дуэли
    DUEL_STARTED = State()            # Игра запущена
    GAME_OVER = State()               # Дуэль закончилась

# Обновление результата игры в чате
async def update_result_message(bot: Bot, callback_query: CallbackQuery, result_message: str):
    await bot.edit_message_reply_markup(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=None
    )
    await bot.send_message(
        chat_id=callback_query.message.chat.id,
        text=result_message
    )

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Добро пожаловать в бота для Международного IT-Форума с участием стран БРИКС и ШОС! Выберите режим игры:", reply_markup=kb.main)

# Функция отправки вопроса с вариантами ответов
async def ask_question(message: Message, state: FSMContext):
    data = await state.get_data()
    current_question = data['question']
    options = current_question['options']

    # Формирование текста вопроса и вариантов ответов
    text = f"{current_question['question']}\n\nВарианты ответов:"
    for index, option in enumerate(options, start=1):
        text += f"\n{index}. {option}"

    # Клавиатура с выбором ответа
    buttons = [
        InlineKeyboardButton(text=str(index + 1), callback_data=f"quiz_{index}") for index in range(len(options))
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons], row_width=len(options))

    # Если есть изображение, отправляем сообщение с изображением
    if current_question.get('image_url'):
        await message.answer_photo(photo=current_question['image_url'], caption=text, reply_markup=keyboard)
    else:
        await message.answer(text=text, reply_markup=keyboard)

# Стартовая команда для запуска викторины
@router.message(F.text == "Стандартная викторина")
async def quiz_start(message: Message, state: FSMContext):
    await message.answer("Правила режима: Тебе отправляются вопросы, посвящённые ХМАО. Твоя задача на них правильно отвечать. В любой момент ты можешь закончить викторину нажав на кнопку 'конец игры', если ты набрал много очков,то проверь таблицу лидеров. Хорошей игры!")
    unused_questions = questions.copy()
    first_question = random.choice(unused_questions)
    unused_questions.remove(first_question)
    await state.update_data(question=first_question, score=0, unused_questions=unused_questions)
    await ask_question(message, state)
    await state.set_state(GameState.WAITING_FOR_ANSWER)

# Обработчик ответа на вопрос
@router.callback_query(lambda c: c.data.startswith("quiz_"), GameState.WAITING_FOR_ANSWER)
async def process_answer(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    answer_index = int(callback_query.data.split("_")[1])
    data = await state.get_data()
    current_question = data['question']
    correct_answer = current_question['answer']
    selected_option = current_question['options'][answer_index]

    result_message = ""
    if selected_option == correct_answer:
        new_score = data.get('score', 0) + 1
        await state.update_data(score=new_score)
        result_message = f"ПРАВИЛЬНО! Ваш счёт: {new_score}"
    else:
        result_message = f"НЕПРАВИЛЬНО. Правильный ответ: {correct_answer}"

    # Предложение дальнейших действий
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Дальше", callback_data="next")],
        [InlineKeyboardButton(text="Конец игры", callback_data="stop")]
    ])

    await bot.send_message(chat_id=callback_query.from_user.id, text=result_message, reply_markup=keyboard)

# Обработчик кнопки "Дальше"
@router.callback_query(lambda c: c.data == "next", GameState.WAITING_FOR_ANSWER)
async def handle_next_button(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    unused_questions = data.get('unused_questions')

    if not unused_questions:
        await end_game(state, callback_query)
        return

    next_question = random.choice(unused_questions)
    unused_questions.remove(next_question)
    await state.update_data(question=next_question, unused_questions=unused_questions)
    await ask_question(callback_query.message, state)

# Обработчик кнопки "Конец игры"
@router.callback_query(lambda c: c.data == "stop", GameState.WAITING_FOR_ANSWER)
async def handle_stop_button(callback_query: CallbackQuery, state: FSMContext):
    await end_game(state, callback_query)

# Логика завершения игры
async def end_game(state: FSMContext, callback_query: CallbackQuery):
    data = await state.get_data()
    final_score = data.get("score", 0)
    username = callback_query.from_user.username or callback_query.from_user.first_name
    # Сохраняем результат в файл
    save_scores(username, final_score)
    await state.clear()
    await bot.send_message(chat_id=callback_query.from_user.id, text=f"Игра закончена. Итоговый счёт: {final_score}")

# Таблица лидеров
@router.message(F.text == "Таблица лидеров")
async def show_leaderboard(message: Message):
    leaders = generate_leaderboard()
    if leaders:
        table = "\n".join([f"{i+1}. {leader['username']}: {leader['score']} очков" for i, leader in enumerate(leaders)])
        await message.answer(f"Таблица лидеров:\n{table}")
    else:
        await message.answer("Пока никто не играл.")

# Банк вопросов
@router.message(F.text == "Банк вопросов")
async def show_full_question_bank(message: Message):
    media = []
    texts = []

    for idx, question in enumerate(questions):
        texts.append(f"{idx+1}. Вопрос: {question['question']}, Варианты ответов: {' '.join(question['options'])}, Правильный ответ: {question['answer']}")

        if question.get("image_url"):
            media.append(InputMediaPhoto(media=question["image_url"], caption=""))

    chunk_size = 10
    chunks = [media[i:i + chunk_size] for i in range(0, len(media), chunk_size)]

    for chunk in chunks:
        await message.answer_media_group(media=chunk)

    for text in texts:
        await message.answer(text)

# 💥 Создание дуэли
@router.message(F.text == "Создать дуэль")
async def create_duel(message: types.Message, state: FSMContext):
    await message.answer("Правила режима: После присоединения второго игрока игра начинается. Двум игрокам отправляется одинаковый вопрос, после того как оба ответят, начнётся следующий раунд. Всего 5 раундов, победит тот, кто наберёт больше очков. Хорошей игры!")
    duel_code = ''.join(random.sample('ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890', k=6))
    active_duels[duel_code] = {
        "initiator_id": message.chat.id,
        "challenger_id": None,
        "rounds": [],
        "used_questions": [],  # Использованные вопросы
        "round_number": 0,
        "max_rounds": 5,
        "players": {},  # Данные по каждому игроку
        "waiting_for_answers": False,  # Флаг ожидания ответов обоих игроков
    }
    await state.update_data(current_duel_code=duel_code)  # Сохраняем код дуэли в состояние
    await bot.send_message(chat_id=message.chat.id, text=f"Дуэль создана. Код дуэли: {duel_code}.\nОтправьте этот код своему оппоненту, чтобы начать игру")

# 🔄 Присоединение к дуэли
@router.message(F.text == "Присоединиться к дуэли")
async def join_duel(message: types.Message, state: FSMContext):
    await message.answer("Правила режима: После того, как вы присоеденитесь - игра начинается. Двум игрокам отправляется одинаковый вопрос, после ответа обоих участников, начнётся следующий раунд. Всего 5 раундов, победит тот, кто наберёт больше очков. Хорошей игры!")
    await message.answer("Введите специальный код дуэли, который вам отправил создатель дуэли")
    await state.set_state(Duels.WAITING_FOR_CODE_INPUT)

# 🔑 Ввод кода дуэли
@router.message(Duels.WAITING_FOR_CODE_INPUT, F.text)
async def input_duel_code(message: types.Message, state: FSMContext):
    duel_code = message.text.strip().upper()
    if duel_code in active_duels and active_duels[duel_code].get("challenger_id") is None:
        active_duels[duel_code]["challenger_id"] = message.chat.id
        await state.update_data(current_duel_code=duel_code)  # Сохраняем код дуэли в состояние
        await bot.send_message(chat_id=active_duels[duel_code]["initiator_id"], text="Оппонент присоединился. Можно начинать дуэль!")
        await bot.send_message(chat_id=message.chat.id, text="Вы присоединились к дуэли. Можно начинать!")
        
        # Начинаем первую партию дуэли
        await prepare_game_for_players(duel_code, state)
    else:
        await message.answer("Неверный код дуэли или дуэль уже занята.")
        await state.clear()

# ✅ Подготовка игры для обоих игроков одновременно (одинаковые вопросы)
async def prepare_game_for_players(duel_code: str, state: FSMContext):
    initiator_id = active_duels[duel_code]["initiator_id"]
    challenger_id = active_duels[duel_code]["challenger_id"]
    
    # Генерация общего случайного вопроса для обоих участников
    unused_questions = questions_with_images.copy()
    common_question = random.choice(unused_questions)
    unused_questions.remove(common_question)

    active_duels[duel_code]["players"] = {
        initiator_id: {"question": common_question, "score": 0, "has_answered": False},  # Добавили флаг has_answered
        challenger_id: {"question": common_question, "score": 0, "has_answered": False}
    }

    active_duels[duel_code]["unused_questions"] = unused_questions
    active_duels[duel_code]["waiting_for_answers"] = True  # Ждем ответы обоих игроков

    # Отправляем одинаковый вопрос обоим игрокам
    await send_first_question_to_all_players(duel_code, common_question)

# Отправляет один и тот же вопрос двум игрокам
async def send_first_question_to_all_players(duel_code: str, question: dict):
    initiator_id = active_duels[duel_code]["initiator_id"]
    challenger_id = active_duels[duel_code]["challenger_id"]

    # Формируем inline-клавиатуру с вариантами ответов
    options_buttons = [[InlineKeyboardButton(text=str(i), callback_data=f"{duel_code}_{i}")] for i in range(1, len(question['options']) + 1)]
    keyboard = InlineKeyboardMarkup(inline_keyboard=options_buttons)

    # Текст вопроса и варианты ответов
    question_text = f"{question['question']}\n\nВарианты ответов:\n" + "\n".join([f"{i}. {opt}" for i, opt in enumerate(question['options'], start=1)])

    # Отправляем идентичный вопрос обоим игрокам
    for player_id in [initiator_id, challenger_id]:
        # Если есть изображение, отправляем фото с вопросом
        if question.get('image_url'):
            await bot.send_photo(
                chat_id=player_id,
                photo=question['image_url'],
                caption=question_text,
                reply_markup=keyboard
            )
        else:
            # Если нет изображения — отправляем только текст вопроса
            await bot.send_message(
                chat_id=player_id,
                text=question_text,
                reply_markup=keyboard
            )

# 🗡️ Обработка выбора ответа игроком
@router.callback_query(lambda c: True)
async def process_answer(callback_query: types.CallbackQuery, state: FSMContext):
    parts = callback_query.data.split('_')
    duel_code = parts[0]
    answer_number = int(parts[1]) - 1

    # Проверяем существование дуэли с таким кодом
    if duel_code not in active_duels:
        return

    duel = active_duels[duel_code]
    initiator_id = duel["initiator_id"]
    challenger_id = duel["challenger_id"]
    players = duel["players"]
    player_id = callback_query.from_user.id

    # Выбираем вопрос конкретного игрока
    question = players[player_id]["question"]
    correct_answer = question["answer"]
    selected_option = question["options"][answer_number]

    # Проверяем правильность ответа
    if selected_option == correct_answer:
        players[player_id]["score"] += 1
        result_message = f"Правильно! Ваш счёт: {players[player_id]['score']}."
    else:
        result_message = f"Неправильно. Правильный ответ: {correct_answer}"

    await bot.send_message(chat_id=player_id, text=result_message)

    # Отмечаем, что игрок ответил
    players[player_id]["has_answered"] = True

    # Проверяем, ответили ли оба игрока
    if all(player["has_answered"] for player in players.values()):
        # Оба игрока ответили, переходим к следующему раунду
        await next_round(duel_code, state)

# ⭐️ Переход к следующему раунду
async def next_round(duel_code: str, state: FSMContext):
    duel = active_duels[duel_code]
    unused_questions = duel["unused_questions"]
    round_number = duel["round_number"] + 1

    duel["round_number"] = round_number

    # Проверяем наличие оставшихся вопросов и лимит матчей
    if unused_questions and round_number <= duel["max_rounds"]:
        next_question = random.choice(unused_questions)
        unused_questions.remove(next_question)

        # Обновляем вопросы для обоих игроков
        players = duel["players"]
        players[duel["initiator_id"]]["question"] = next_question
        players[duel["challenger_id"]]["question"] = next_question
        players[duel["initiator_id"]]["has_answered"] = False
        players[duel["challenger_id"]]["has_answered"] = False

        # Отправляем следующий вопрос обоим игрокам
        await send_first_question_to_all_players(duel_code, next_question)
    else:
        # Заканчиваем игру и сообщаем результаты
        await finish_duel(duel_code)

# 🎯 Итог дуэли
async def finish_duel(duel_code: str):
    duel = active_duels.pop(duel_code)
    initiator_id = duel["initiator_id"]
    challenger_id = duel["challenger_id"]
    players = duel["players"]

    initiator_username = (await bot.get_chat(initiator_id)).username or (await bot.get_chat(initiator_id)).first_name
    challenger_username = (await bot.get_chat(challenger_id)).username or (await bot.get_chat(challenger_id)).first_name

    initiator_score = players[initiator_id]["score"]
    challenger_score = players[challenger_id]["score"]

    # Сохраняем результаты дуэли
    save_scores(initiator_username, initiator_score)
    save_scores(challenger_username, challenger_score)

    if initiator_score > challenger_score:
        result_message = f"Дуэль закончена! Победил создатель дуэли ({initiator_username}) со счётом {initiator_score}:{challenger_score}."
    elif challenger_score > initiator_score:
        result_message = f"Дуэль закончена! Победил присоеденившийся игрок ({challenger_username}) со счётом {challenger_score}:{initiator_score}."
    else:
        result_message = f"Дуэль завершилась вничью со счётом :{challenger_score}:{initiator_score}."

    # Сообщаем результат обоим игрокам
    await bot.send_message(chat_id=initiator_id, text=result_message)
    await bot.send_message(chat_id=challenger_id, text=result_message)