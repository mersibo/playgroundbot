import sqlite3
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from datetime import time, timedelta
from telegram.ext import JobQueue
from io import BytesIO
import os
from config import API_TOKEN
from init_db import init_db, populate_initial_data

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'mov', 'wav'}

# Определяем этапы разговора
FIRST_NAME, LAST_NAME, CITY, AGE, INTERESTS, CHAMPIONSHIP, VIDEO, HOW_TO_BECOME_AUTHOR, START_NOW, START_LATER, PLATFORM_INFO, MISSION, KARMA, FINAL_VIDEO, FINAL_TEST, FIRST_BLOCK_DONE, FIRST_QUESTION, QUIZ_POLICY, QUIZ_FACTS, QUIZ_BEAUTIFUL, START_TRAINING, TEST_VIDEO, TEST_BLOCK, CONTINUE_EDUCATION, START_FOURH_BLOCK, TEST_RULES, CONTINUE_FOURH_BLOCK, TEST_GUIDELINE, START_FIFTH_BLOCK, TEST_DISTRIBUTION, DISTRIBUTION_OVERVIEW, TEST_NEXT, ANALYZE_CASES, START_FEEDBACK, GET_FEEDBACK, GET_USEFUL_INFO, GET_USELESS_INFO, GET_WANTED_INFO, GET_AUTHOR_DECISION, GET_FINAL_FEEDBACK, END = range(41)

def get_bot_text(key):
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM bot_texts WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    else:
        return None

def get_bot_files(key):
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT response_content, response_type FROM menu_items WHERE callback_data = ?", (key,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return result
    else:
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Функция для получения текста и файлов из базы данных
def get_text_and_files(key):
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()

    # Получаем текст по ключу
    cursor.execute("SELECT content FROM bot_texts WHERE key = ?", (key,))
    text_result = cursor.fetchone()
    content = text_result[0] if text_result else "Текст не найден."

    # Получаем файлы по ключу
    cursor.execute("SELECT file_name, file_type FROM bot_files WHERE bot_text_key = ?", (key,))
    files = cursor.fetchall()
    conn.close()

    return content, files

# Функция для отправки сообщения
def send_message_with_files(update: Update, context: CallbackContext, key: str):
    query = update.callback_query
    try:
        chat_id = update.message.chat_id
    except:
        chat_id = query.message.chat_id
       
    content, files = get_text_and_files(key)

    try:
        update.message.reply_text(content)
    except:
        query.message.reply_text(content)

    # Отправка файлов
    for file_name, file_type in files:
        file_path = os.path.join(UPLOAD_FOLDER, file_name)
        
        if allowed_file(file_name):
            try:
                if file_type == 'video':
                    with open(file_path, 'rb') as file:
                        context.bot.send_video(chat_id=chat_id, video=InputFile(file))
                elif file_type == 'image':
                    with open(file_path, 'rb') as file:
                        context.bot.send_photo(chat_id=chat_id, photo=InputFile(file))
                elif file_type == 'document':
                    with open(file_path, 'rb') as file:
                        context.bot.send_document(chat_id=chat_id, document=InputFile(file))
                elif file_type == 'audio':
                    with open(file_path, 'rb') as file:
                        context.bot.send_audio(chat_id=chat_id, audio=InputFile(file))
                else:
                    pass
            except Exception as e:
                logging.error(f"Ошибка при отправке файла: {e}")
                update.message.reply_text(f"Произошла ошибка при отправке файла: {str(e)}")

def save_user_to_db(context: CallbackContext):
    # Получаем данные пользователя из context.user_data
    chat_id = context.user_data.get('chat_id')
    username = context.user_data.get('username')
    first_name = context.user_data.get('first_name')
    last_name = context.user_data.get('last_name')
    city = context.user_data.get('city')
    age = context.user_data.get('age')

    # Подключение к базе данных
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()

    # Проверка, существует ли уже пользователь в базе данных
    cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    user_exists = cursor.fetchone()

    if user_exists:
        logger.info("Пользователь с chat_id %s уже существует в базе данных.", chat_id)
    else:
        # Вставка данных пользователя в таблицу
        cursor.execute('''
            INSERT INTO users (chat_id, username, first_name, last_name, city, age)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (chat_id, username, first_name, last_name, city, age))
        
        conn.commit()
        logger.info("Данные пользователя сохранены в базе данных.")

    # Закрытие соединения с базой данных
    conn.close()

def start(update: Update, context: CallbackContext):
    logger.info("Команда /start вызвана")
    
    # Сохранение chat_id и username пользователя
    chat_id = update.message.chat_id
    username = update.message.from_user.username

    context.user_data['chat_id'] = chat_id
    context.user_data['username'] = username
    
    # Получение сообщения приветствия из базы данных
    send_message_with_files(update, context, 'welcome_message')

    keyboard = [[InlineKeyboardButton("Давай", callback_data='start_info')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text("Нажмите кнопку ниже, чтобы продолжить.", reply_markup=reply_markup)

    return FIRST_NAME

def start_info(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    logger.info("Callback start_info вызван от пользователя %s", query.from_user.username)
    
    # Запрос на ввод имени
    send_message_with_files(update, context, 'welcome_1')
    
    return FIRST_NAME

def first_name(update: Update, context: CallbackContext):
    first_name = update.message.text
    logger.info("Получено имя: %s", first_name)

    context.user_data['first_name'] = first_name
    
    # Запрос на ввод фамилии
    send_message_with_files(update, context, 'welcome_2')
    
    return LAST_NAME

def last_name(update: Update, context: CallbackContext):
    last_name = update.message.text
    logger.info("Получена фамилия: %s", last_name)

    context.user_data['last_name'] = last_name
    
    # Запрос на ввод города
    send_message_with_files(update, context, 'welcome_3')
    
    return CITY

def city(update: Update, context: CallbackContext):
    city = update.message.text
    context.user_data['city'] = city
    logger.info("Получен город: %s", city)
    
    # Опрос по возрасту
    age_poll_keyboard = [
        [InlineKeyboardButton("Меньше 15", callback_data='age_1')],
        [InlineKeyboardButton("16-17", callback_data='age_2')],
        [InlineKeyboardButton("18-20", callback_data='age_3')],
        [InlineKeyboardButton("Больше 20", callback_data='age_4')]
    ]
    reply_markup = InlineKeyboardMarkup(age_poll_keyboard)

    send_message_with_files(update, context, 'welcome_4')
    update.message.reply_text(
        "Выберите вариант ответа:",
        reply_markup=reply_markup
    )
    
    return AGE

def age(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    age = query.data.replace('age_', '')
    context.user_data['age'] = age
    
    # Запрос интересов пользователя
    send_message_with_files(update, context, 'welcome_5')
    
    return INTERESTS

def interests(update: Update, context: CallbackContext):
    interests = update.message.text
    logger.info("Получены интересы: %s", interests)

    context.user_data['interests'] = interests
    
    # Опрос по участию в Чемпионате
    championship_poll_keyboard = [
        [InlineKeyboardButton("1", callback_data='championship_1')],
        [InlineKeyboardButton("2", callback_data='championship_2')],
        [InlineKeyboardButton("3", callback_data='championship_3')],
        [InlineKeyboardButton("4", callback_data='championship_4')],
        [InlineKeyboardButton("Я не финалист Чемпионата", callback_data='championship_5')]
    ]
    reply_markup = InlineKeyboardMarkup(championship_poll_keyboard)

    send_message_with_files(update, context, 'welcome_6')
    update.message.reply_text("Выберите вариант ответа:", reply_markup=reply_markup)
    
    return CHAMPIONSHIP

def championship(update: Update, context: CallbackContext):
    query = update.callback_query
    context.user_data['championship'] = query.data.replace('championship_', '')
    save_user_to_db(context)
    send_message_with_files(update, context, 'welcome_7')
    query.message.reply_text(
        "Готов?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Поехали!", callback_data='video_start')]
        ])
    )
    
    return VIDEO

def video(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    chat_id = query.message.chat_id
    
    send_message_with_files(update, context, 'welcome_8')

    try:
        video_path = "output.mp4"
        with open(video_path, 'rb') as video_file:
            context.bot.send_video_note(chat_id=chat_id, video_note=InputFile(video_file))
    except Exception as e:
        query.message.reply_text(f"Произошла ошибка: {str(e)}")
    
    query.message.reply_text(
       "Продолжим?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Как стать автором?", callback_data='author')]
        ])
    )
    
    return HOW_TO_BECOME_AUTHOR

def how_to_become_author(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Отправка картинки с описанием
    photo_path = "Молодежная редакция 2024-25 уч.год.png"  # Замените на путь к вашей картинке
    caption = (
        "Путь в редакции состоит из нескольких последовательных этапов от участника (ты здесь) до стажера, "
        "а затем автора или даже куратора команды. Перескочить какой-то из этапов нельзя, но можно пройти в своем темпе – кто-то быстрее, кто-то дольше."
    )

    try:
        with open(photo_path, 'rb') as photo_file:
            context.bot.send_photo(chat_id=query.message.chat_id, photo=InputFile(photo_file), caption=caption)
    except Exception as e:
        logger.error(f"Error sending photo: {e}")
        query.message.reply_text("Произошла ошибка при отправке фотографии.")

    # Отправляем первое сообщение с кнопкой
    send_message_with_files(update, context, 'welcome_9')
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Из чего состоит Площадка?", callback_data='platform_info')]
    ])
    query.message.reply_text("Продолжим?", reply_markup=reply_markup)

    return HOW_TO_BECOME_AUTHOR

def platform_info(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    # Отправляем сообщение о блоках
    send_message_with_files(update, context, 'welcome_10')

    # Планируем следующие сообщения
    context.job_queue.run_once(send_blocks_description, 20, context=query.message.chat_id)
    context.job_queue.run_once(send_final_message, 40, context=query.message.chat_id)

def send_blocks_description(context: CallbackContext):
    message = get_bot_text('welcome_11')
    chat_id = context.job.context
    context.bot.send_message(chat_id=chat_id, text=message)

def send_final_message(context: CallbackContext):
    chat_id = context.job.context
    message = get_bot_text('welcome_12')
    context.bot.send_message(chat_id=chat_id, text=message, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать обучение", callback_data='start_now')],
        [InlineKeyboardButton("Начать позже", callback_data='start_later')]
    ]))

def start_education(update: Update, context: CallbackContext):
    send_message_with_files(update, context, 'welcome_13')

def start_later(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id
    fullname = context.user_data.get('fullname', 'друг')

    # Отправляем сообщение пользователю
    send_message_with_files(update, context, 'welcome_14')

    # Настраиваем ежедневное напоминание
    schedule_reminder(context, chat_id, fullname)
    
    query.answer()
    

def start_now(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    send_message_with_files(update, context, 'start_first_block')
    query.message.reply_text("Ты готов? Если да, то нажимай!", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Пройти тест", callback_data='test_mission')]
    ]))
    
    return MISSION

def test_mission(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    send_message_with_files(update, context, 'first_block_1')
    options = [
        InlineKeyboardButton("1", callback_data='mission_incorrect'),
        InlineKeyboardButton("2", callback_data='mission_correct'),
        InlineKeyboardButton("3", callback_data='mission_incorrect')
    ]
    reply_markup = InlineKeyboardMarkup([options])
    query.message.reply_text("Выберите вариант ответа:", reply_markup=reply_markup)
    
    return KARMA

def handle_mission_response(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'mission_correct':
        response = (
            "Да, именно на это направлена вся наша работа. Мы, конечно, будем наполнять контентом ресурсы Чемпионата, "
            "а также будем предлагать стажировки и работу нашим авторам, но это лишь часть наших задач, объединенных общей миссией."
        )
        next_button = InlineKeyboardButton("Продолжить погружение в редакцию", callback_data='continue_education')
    else:
        response = (
            "Нет, миссия у нас другая. Посмотри еще раз видео и возвращайся к прохождению теста."
        )
        next_button = InlineKeyboardButton("Пройти тест еще раз", callback_data='test_mission')
    
    query.message.reply_text(response, reply_markup=InlineKeyboardMarkup([[next_button]]))
    
    return KARMA

def continue_education(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    send_message_with_files(update, context, 'first_block_2')
    query.message.reply_text("Ты готов? Если да, то нажимай!", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Пройти тест", callback_data='test_roles')]
    ]))
    
    return FINAL_VIDEO

def test_roles(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    send_message_with_files(update, context, 'first_block_3')
    options = [
        InlineKeyboardButton("1", callback_data='roles_incorrect'),
        InlineKeyboardButton("2", callback_data='roles_correct'),
        InlineKeyboardButton("3", callback_data='roles_incorrect')
    ]
    reply_markup = InlineKeyboardMarkup([options])
    query.message.reply_text("Выберите вариант ответа", reply_markup=reply_markup)
    
    return KARMA

def handle_roles_response(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'roles_correct':
        response = (
            "Да, именно такой путь и проходят участники редакции. Приготовься ответить на следующий вопрос."
        )
        next_button = InlineKeyboardButton("Продолжить", callback_data='test_karma')
    else:
        response = (
            "Нет, порядок другой. Посмотри еще раз видео и возвращайся к прохождению теста."
        )
        next_button = InlineKeyboardButton("Пройти тест еще раз", callback_data='test_roles')
    
    query.message.reply_text(response, reply_markup=InlineKeyboardMarkup([[next_button]]))
    
    return KARMA

def test_karma(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    send_message_with_files(update, context, 'first_block_4')
    options = [
        InlineKeyboardButton("5", callback_data='karma_incorrect'),
        InlineKeyboardButton("0.5", callback_data='karma_incorrect'),
        InlineKeyboardButton("3", callback_data='karma_correct')
    ]
    reply_markup = InlineKeyboardMarkup([options])
    query.message.reply_text("Выберите вариант ответа:", reply_markup=reply_markup)
    
    return FINAL_VIDEO

def handle_karma_response(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'karma_correct':
        response = (
            "Да, все верно. С такими успехами в изучении материалов у тебя есть все шансы быстро заработать эти плюсы. "
            "А сейчас как настроение? Продолжаем учиться?"
        )
        next_buttons = [
            InlineKeyboardButton("Продолжить погружение", callback_data='final_video'),
            InlineKeyboardButton("Сделать перерыв", callback_data='take_break')
        ]
    else:
        response = (
            "Нет, цифры в шкале плюсов в карму другие. Посмотри еще раз видео и возвращайся к прохождению теста."
        )
        next_buttons = [InlineKeyboardButton("Пройти тест еще раз", callback_data='test_karma')]
    
    query.message.reply_text(response, reply_markup=InlineKeyboardMarkup([next_buttons]))
    
    return FINAL_VIDEO

def final_video(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    send_message_with_files(update, context, 'first_block_5')
    query.message.reply_text("Ты готов? Если да, то нажимай!", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Пройти тест", callback_data='final_test')]
    ]))
    
    return FIRST_BLOCK_DONE

def final_test(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    send_message_with_files(update, context, 'first_block_6')
    options = [
        InlineKeyboardButton("1", callback_data='final_incorrect'),
        InlineKeyboardButton("2", callback_data='final_incorrect'),
        InlineKeyboardButton("3", callback_data='final_correct')
    ]
    reply_markup = InlineKeyboardMarkup([options])
    query.message.reply_text("Выберите вариант ответа:", reply_markup=reply_markup)
    
    return FIRST_BLOCK_DONE

def handle_final_test_response(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'final_correct':
        response = (
            "Да, именно это и делают команды Запишем. Совсем скоро и ты сможешь попасть в такую. "
            "А в завершении этого блока хотим напомнить, что Молодежная редакция создана как комфортное место для всех его участников, "
            "это ваш сейф-спейс, тут можно быть собой и не стесняться своих хобби и интересов. А чтобы так и было, каждому важно "
            "понимать, как уважать друг друга и выстраивать экологичное общение в коллективе. Прочитай нашу памятку и сохрани себе. "
            "Уверены, что у тебя все получится. А если будут сложности, всегда рядом кураторы и руководители редакции. Даже если "
            "начинается конфликт – не доводи его до бурлящего котла, все можно решить на ранней стадии."
        )
        next_button = InlineKeyboardButton("Памятка прочитана и усвоена!", callback_data='first_block_done')
    else:
        response = (
            "Нет, задача у команды другая. Посмотри еще раз видео и возвращайся к прохождению теста."
        )
        next_button = InlineKeyboardButton("Пройти тест еще раз", callback_data='final_test')
    
    query.message.reply_text(response, reply_markup=InlineKeyboardMarkup([[next_button]]))
    
    return FIRST_BLOCK_DONE

def first_block_done(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    send_message_with_files(update, context, 'first_block_final')
    query.message.reply_text("Идем дальше, или сделаем перерыв?", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать обучение", callback_data='start_now_1')],
        [InlineKeyboardButton("Начать позже", callback_data='start_later')]
    ]))
    
    

def start_second_block(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    logger.info(f"start_second_block вызван от пользователя {query.from_user.username}")

    send_message_with_files(update, context, 'start_second_block')
    
    return FIRST_QUESTION  # Переход в состояние ожидания текстового ответа

def first_question(update: Update, context: CallbackContext):
    user_response = update.message.text
    user_name = update.message.from_user.first_name

    send_message_with_files(update, context, 'second_block_1')
    context.bot.send_message(chat_id=update.message.chat_id, text="Идем дальше, или сделаем перерыв?", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать обучение", callback_data='start_now_2')],
        [InlineKeyboardButton("Начать позже", callback_data='start_later')]
    ]))

def second_block_2(update:Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, 'second_block_2')
    button = InlineKeyboardButton("Пройти тест", callback_data='quiz_policy')
    query.message.reply_text("Ты готов?", reply_markup=InlineKeyboardMarkup([[button]]))


def quiz_policy(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "second_block_3")
    options = [
        InlineKeyboardButton("1", callback_data="policy_wrong"),
        InlineKeyboardButton("2", callback_data="policy_wrong"),
        InlineKeyboardButton("3", callback_data="policy_correct")
    ]

    query.message.reply_text(text="Выберите вариант ответа:", reply_markup=InlineKeyboardMarkup([options]))
    return QUIZ_POLICY


def quiz_facts(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == "policy_wrong":
        query.message.reply_text(
            "Нет, редполитика преследует другие цели. Посмотри еще раз видео и возвращайся к прохождению теста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пройти тест еще раз", callback_data="quiz_policy")]
            ])
        )
        return QUIZ_POLICY

    query.message.reply_text(
        "Да, именно для этого в редакции существует документ со стандартами. Пора поближе познакомиться с принципами Молодежной редакции.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Перейти к знакомству", callback_data="quiz_facts")]
        ])
    )
    return QUIZ_FACTS

def pre_quiz_beautiful(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "second_block_4")
    
    button = InlineKeyboardButton("Пройти тест", callback_data='quiz_beautiful')
    query.message.reply_text("Ты готов?", reply_markup=InlineKeyboardMarkup([[button]]))

def quiz_beautiful(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "second_block_5")
    options = [
        InlineKeyboardButton("1", callback_data="beauty_wrong"),
        InlineKeyboardButton("2", callback_data="beauty_correct"),
        InlineKeyboardButton("3", callback_data="beauty_wrong")
    ]

    query.message.reply_text(text="Выберите вариант ответа:", reply_markup=InlineKeyboardMarkup([options]))
    return QUIZ_FACTS


def handle_beautiful_response(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == "beauty_wrong":
        query.message.reply_text(
            "Нет, по фактам о другом. Посмотри еще раз видео и возвращайся к прохождению теста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пройти тест еще раз", callback_data="quiz_facts")]
            ])
        )
        return QUIZ_FACTS


    send_message_with_files(update, context, "second_block_6")
    options = [
        InlineKeyboardButton("1", callback_data="krasivo_wrong"),
        InlineKeyboardButton("2", callback_data="krasivo_wrong"),
        InlineKeyboardButton("3", callback_data="krasivo_correct")
    ]

    query.message.reply_text(text="Выберите вариант ответа:", reply_markup=InlineKeyboardMarkup([options]))
    return QUIZ_BEAUTIFUL


def handle_quiz_completion(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == "krasivo_wrong":
        query.message.reply_text(
            "Это, конечно, красиво, но наш принцип о другом. Посмотри еще раз видео и возвращайся к прохождению теста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пройти тест еще раз", callback_data="quiz_beautiful")]
            ])
        )
        return QUIZ_BEAUTIFUL

    query.message.reply_text(
        "Да, красиво для нас – это в соответствии с редакционными стандартами (верными кавычками, большими буквами и обращениями в нужном формате). Ответ верный.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Продолжить погружение в редакцию", callback_data="quiz_complete")]
        ])
    )
    return FIRST_BLOCK_DONE

def second_block_pre_final(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "second_block_pre_final")
    query.message.reply_text("Все было понятно?", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Редполитика изучена!", callback_data='policy_learned')],
    ]))

def second_block_final(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "second_block_final")
    query.message.reply_text("Идем дальше, или сделаем перерыв?", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать обучение", callback_data='start_now_second')],
        [InlineKeyboardButton("Начать позже", callback_data='start_later_second')]
    ]))

def start_training(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "start_third_block")
    keyboard = [[InlineKeyboardButton("Пройти тест по видео", callback_data='test_video')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text="Ты готов?",
        reply_markup=reply_markup
    )
    return TEST_VIDEO

# Первый тест
def test_video(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "third_block_1")
    options = [
        InlineKeyboardButton("1", callback_data='video_correct'),
        InlineKeyboardButton("2", callback_data='video_wrong'),
        InlineKeyboardButton("3", callback_data='video_wrong')
    ]
    query.message.reply_text(text="Выберите вариант ответа:", reply_markup=InlineKeyboardMarkup([options]))
    return TEST_VIDEO

# Обработка ответа на первый тест
def handle_test_video_response(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == 'video_correct':
        query.message.reply_text(
            text=(
                "Да, план – это неотъемлемая часть подготовки текста. "
                "А чтобы вам было проще, у нас есть [пример](https://docs.google.com/document/d/1_psEGAbDgupmqeIwOp-4no7uB3z3F2_QoZy-WH5lq0s/edit?usp=sharing), "
                "в каком виде его нужно приносить редактору. Копируй себе этот гугл-документ, удаляй пример и заполняй свой план текста."
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Продолжить погружение в редакцию", callback_data='video_continue_education')]
            ])
        )
        return CONTINUE_EDUCATION
    else:
        query.message.reply_text(
            text="Нет, на самом старте работы нужно сделать другое. Посмотри еще раз видео и возвращайся к прохождению теста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пройти тест еще раз", callback_data='test_video')]
            ])
        )
        return TEST_VIDEO

# Продолжение обучения
def video_continue_education(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "third_block_2")
    keyboard = [[InlineKeyboardButton("Пройти тест по блоку", callback_data='test_block')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text="Ты готов?",
        reply_markup=reply_markup
    )
    return TEST_BLOCK

# Второй тест
def test_block(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "third_block_3")
    options = [
        InlineKeyboardButton("1", callback_data='plan_wrong'),
        InlineKeyboardButton("2", callback_data='plan_correct'),
        InlineKeyboardButton("3", callback_data='plan_wrong')
    ]
    query.message.reply_text(text="Выберите вариант ответа", reply_markup=InlineKeyboardMarkup([options]))
    return TEST_BLOCK

# Обработка ответа на второй тест
def handle_test_block_response(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == 'plan_correct':
        query.message.reply_text(
            text="Да, все верно.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Продолжить погружение в редакцию", callback_data='third_block_continue')]
            ])
        )
        return CONTINUE_EDUCATION
    else:
        query.message.reply_text(
            text="Нет, параллельная структура – это другое. Посмотри еще раз видео и возвращайся к прохождению теста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пройти тест еще раз", callback_data='test_block')]
            ])
        )
        return TEST_BLOCK

def third_block_pre_final(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "third_block_4")

    query.message.reply_text(
            text="Нажимай и поехали дальше!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Принято, понято", callback_data='third_block_final')]
            ])
        )

def third_block_final(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "third_block_final")
    query.message.reply_text("Идем дальше, или сделаем перерыв?", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать обучение", callback_data='start_now_third')],
        [InlineKeyboardButton("Начать позже", callback_data='start_later_third')]
    ]))

def start_fourh_block(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "start_fourh_block")
    keyboard = [[InlineKeyboardButton("Пройти тест", callback_data='test_rules')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text="Ты готов?",
        reply_markup=reply_markup
    )
    return TEST_RULES

# Первый тест
def test_rules(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "fourh_block_1")
    options = [
        InlineKeyboardButton("1", callback_data='rules_wrong'),
        InlineKeyboardButton("2", callback_data='rules_wrong'),
        InlineKeyboardButton("3", callback_data='rules_correct')
    ]
    query.message.reply_text(text="Выберите вариант ответа:", reply_markup=InlineKeyboardMarkup([options]))
    return TEST_RULES

# Обработка ответа на первый тест
def handle_test_rules_response(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == 'rules_correct':
        query.message.reply_text(
            text=(
                "Все так, без разрешения эксперта нельзя включать запись. Общаться с героем на ты, конечно, можно. А изучить его нужно еще до старта "
                "интервью – это часть твоей подготовки."
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Продолжить погружение в редакцию", callback_data='continue_fourh_block')]
            ])
        )
        return CONTINUE_EDUCATION
    else:
        query.message.reply_text(
            text="Правила - это важно, но только если они верные. Посмотри видео еще раз и возвращайся к тесту.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пройти тест еще раз", callback_data='test_rules')]
            ])
        )
        return TEST_RULES

# Продолжение обучения
def continue_fourh_block(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    send_message_with_files(update, context, "fourh_block_2")
    keyboard = [[InlineKeyboardButton("Принято, перейти к тесту по памятке", callback_data='test_guideline')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text="А сейчас будет тест",
        reply_markup=reply_markup
    )
    return TEST_GUIDELINE

# Второй тест
def test_guideline(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "fourh_block_3")
    options = [
        InlineKeyboardButton("1", callback_data='guid_wrong'),
        InlineKeyboardButton("2", callback_data='guid_correct'),
        InlineKeyboardButton("3", callback_data='guid_wrong')
    ]
    query.message.reply_text(text="Выберите вариант ответа:", reply_markup=InlineKeyboardMarkup([options]))
    return TEST_GUIDELINE

# Обработка ответа на второй тест
def handle_test_guideline_response(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == 'guid_correct':
        query.message.reply_text(
            text=(
                "Да, все верно. Слова-паразиты, штампы и канцеляризмы мешают воспринимать информацию, поэтому их нужно редактировать. Все верно!"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Продолжить погружение в редакцию", callback_data='fourh_block_final')]
            ])
        )
        return CONTINUE_EDUCATION
    else:
        query.message.reply_text(
            text="Нет, как раз это можно оставить, если текст получается органичным и эти особенности речи эксперта не мешают цели контента. Не нужно делать совсем сухой текст.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пройти тест еще раз", callback_data='test_guideline')]
            ])
        )
        return TEST_GUIDELINE

def fourh_block_final(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    send_message_with_files(update, context, "fourh_block_final")

    query.message.reply_text("Идем дальше, или сделаем перерыв?", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать обучение", callback_data='start_now_fourh')],
        [InlineKeyboardButton("Начать позже", callback_data='start_later_fourh')]
    ]))

# Начало обучения
def start_fifth_block(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "start_fifth_block")
    keyboard = [[InlineKeyboardButton("Пройти тест", callback_data='test_distribution')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text="Нажимай только если внимательно все прочитал",
        reply_markup=reply_markup
    )
    return TEST_DISTRIBUTION

# Тест по дистрибуции
def test_distribution(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "fifth_block_1")
    options = [
        InlineKeyboardButton("1", callback_data='dis_wrong'),
        InlineKeyboardButton("2", callback_data='dis_wrong'),
        InlineKeyboardButton("3", callback_data='dis_correct')
    ]
    query.message.reply_text(text="Выберите вариант ответа:", reply_markup=InlineKeyboardMarkup([options]))
    return TEST_DISTRIBUTION

# Обработка ответа на тест
def handle_test_distribution_response(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == 'dis_correct':
        query.message.reply_text(
            text=(
                "Да, все верно. Теперь ты знаешь теорию, и мы перейдем к развитию твоей насмотренности.\n\n"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Перейти дальше", callback_data='distribution_overview')]
            ])
        )
        return DISTRIBUTION_OVERVIEW
    else:
        query.message.reply_text(
            text="К сожалению, это не так. Посмотри еще раз гайд и возвращайся к прохождению теста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пройти тест еще раз", callback_data='test_distribution')]
            ])
        )
        return TEST_DISTRIBUTION

# Обзор по дистрибуции
def distribution_overview(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "fifth_block_2")
    keyboard = [[InlineKeyboardButton("Принято, понято", callback_data='pre_test_next')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text="Все было понятно?",
        reply_markup=reply_markup
    )
    return TEST_NEXT

def pre_next_test(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "fifth_block_3")
    query.message.reply_text(
            text="Ты готов к тесту?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Перейти к тесту", callback_data='test_next')]
            ])
        )

# Второй тест
def test_next(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "fifth_block_4")
    options = [
        InlineKeyboardButton("1", callback_data='next_wrong'),
        InlineKeyboardButton("2", callback_data='next_wrong'),
        InlineKeyboardButton("3", callback_data='next_wrong'),
        InlineKeyboardButton("4", callback_data='next_correct')
    ]
    query.message.reply_text(text="Выберите вариант ответа:", reply_markup=InlineKeyboardMarkup([options]))
    return TEST_NEXT

# Обработка ответа на второй тест
def handle_test_next_response(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    if query.data == 'next_correct':
        query.message.reply_text(
            text=(
                "Да, все верно. Каналы дистрибуции могут быть самыми разными от надписи на заборе до огромного рекламного баннера в центре города. Настало время самостоятельно изучать кейсы и посмотреть лучшие практики на рынке дистрибуции контента."
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Перейти дальше", callback_data='analyze_cases')]
            ])
        )
        return ANALYZE_CASES
    else:
        query.message.reply_text(
            text="К сожалению, это не так. Посмотри еще раз гайд и возвращайся к прохождению теста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пройти тест еще раз", callback_data='test_next')]
            ])
        )
        return TEST_NEXT

# Анализ кейсов
def analyze_cases(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "fifth_block_5")
    keyboard = [[InlineKeyboardButton("Круто, давайте дальше", callback_data='fifth_block_final')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text="Круто же?",
        reply_markup=reply_markup
    )

def fifth_block_final(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    send_message_with_files(update, context, "fifth_block_final")

    return START_FEEDBACK

def start_feedback(update: Update, context: CallbackContext) -> int:
    send_message_with_files(update, context, "start_finish")
    return GET_USEFUL_INFO

# Получение самой полезной информации
def get_useful_info(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text
    context.user_data['useful_info'] = user_response[:100]  # Обрезаем до 100 символов
    send_message_with_files(update, context, "finish_1")
    return GET_USELESS_INFO

# Получение неинтересной информации
def get_useless_info(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text
    context.user_data['useless_info'] = user_response[:100]  # Обрезаем до 100 символов
    send_message_with_files(update, context, "finish_2")
    return GET_WANTED_INFO

# Получение информации о том, что хотелось бы узнать
def get_wanted_info(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text
    context.user_data['wanted_info'] = user_response[:100]  # Обрезаем до 100 символов


    keyboard = [
        [InlineKeyboardButton("Да, точно хочу", callback_data='yes')],
        [InlineKeyboardButton("Нет", callback_data='no')],
        [InlineKeyboardButton("Пока думаю", callback_data='maybe')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    send_message_with_files(update, context, "finish_3")
    update.message.reply_text(
        text="Выбери свой вариант",
        reply_markup=reply_markup
    )
    return GET_AUTHOR_DECISION

# Получение решения о становлении автором
def get_author_decision(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    context.user_data['author_decision'] = query.data

    send_message_with_files(update, context, "finish_4")
    return GET_FINAL_FEEDBACK

# Получение финального фидбека
def get_final_feedback(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text
    context.user_data['final_feedback'] = user_response[:100]  # Обрезаем до 100 символов
    chat_id = update.message.chat_id
    update.message.reply_text(
        "Урааааа! Теперь вводный образовательный курс в Молодежную редакцию завершен. Поздравляем и очень гордимся!"
    )

    send_message_with_files(update, context, "finish_final_1")
    try:
        video_path = "Завершение.mp4"
        with open(video_path, 'rb') as video_file:
            context.bot.send_video_note(chat_id=chat_id, video_note=InputFile(video_file))
    except Exception as e:
        update.message.reply_text(f"Произошла ошибка: {str(e)}")

    send_message_with_files(update, context, "finish_final_2")
    return END

def start_later(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.message.chat_id
    fullname = context.user_data.get('fullname', 'друг')
    
    query.message.reply_text(
        "Принято. Завтра напомним о себе. Хорошего тебе дня! А если захочешь зайти раньше просто нажми на кнопку «Продолжить погружение».",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Продолжить погружение", callback_data='start_now')]
        ])
    )
    
    # Настраиваем ежедневное напоминание
    schedule_reminder(context, chat_id, fullname)
    
    query.answer()
   

def take_break(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    query.message.reply_text(
        "Принято. Завтра напомним о себе. Хорошего тебе дня! А если захочешь зайти раньше просто нажми на кнопку «Продолжить погружение».",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Продолжить погружение", callback_data='start_now')]
        ])
    )
    
    # Настраиваем ежедневное напоминание
    schedule_reminder(context, chat_id=query.message.chat_id, fullname=context.user_data.get('fullname', 'друг'))
    
    return ConversationHandler.END


def send_reminder(context: CallbackContext):
    job = context.job
    chat_id = job.context['chat_id']
    fullname = job.context['fullname']

    context.bot.send_message(
        chat_id=chat_id,
        text=f"Тук-тук … А {fullname} выйдет сегодня на Площадку? Если да – нажми на кнопку Начать обучение, расположенную выше."
    )

def schedule_reminder(context: CallbackContext, chat_id, fullname):
    # Настройка ежедневного напоминания в 12:00 по МСК
    job_queue = context.job_queue
    job_context = {'chat_id': chat_id, 'fullname': fullname}
    
    # Определяем время 12:00 по МСК (UTC+3)
    reminder_time = time(hour=9, minute=0)  # 12:00 по МСК соответствует 9:00 по UTC
    
    # Добавляем задачу в очередь с контекстом chat_id и fullname
    job_queue.run_daily(send_reminder, reminder_time, context=job_context)

def menu(update: Update, context: CallbackContext):
    logger.info("Команда /menu вызвана")
    
    # Создаем Inline-кнопку "Связаться с администратором"
    keyboard = [
        [InlineKeyboardButton(text="Связаться с администратором", callback_data="contact_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправка сообщения с кнопкой
    update.message.reply_text(
        "Если у вас возникли вопросы, вы можете связаться с администратором:",
        reply_markup=reply_markup
    )

def contact_admin(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    chat_id = query.message.chat_id
    with sqlite3.connect('playground_bot.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contact_requests WHERE chat_id = ?", (chat_id,))
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO contact_requests (chat_id) VALUES (?)", (chat_id,))
            conn.commit()
            query.message.reply_text("Ваш запрос отправлен администратору. Ожидайте ответа.")
        else:
            query.message.reply_text("Вы уже отправляли запрос. Пожалуйста, дождитесь ответа.")


def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = query.from_user.id
    logger.info(f"Callback query received: {query.data}")

    try:
        # Обработка нажатий кнопок в различных этапах диалога
        if query.data.startswith("age_"):
            return age(update, context)
        elif query.data.startswith("championship_"):
            return championship(update, context)
        elif query.data == "video_start":
            return video(update, context)
        elif query.data == "start_now":
            return start_now(update, context)
        elif query.data == "start_later":
            return start_later(update, context)
        elif query.data == "contact_admin":
            # Обработка запроса на контакт с администратором
            with sqlite3.connect('playground_bot.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM contact_requests WHERE chat_id = ?", (chat_id,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("INSERT INTO contact_requests (chat_id) VALUES (?)", (chat_id,))
                    conn.commit()
                    query.message.reply_text("Ваш запрос отправлен администратору. Ожидайте ответа.")
                else:
                    query.message.reply_text("Вы уже отправляли запрос. Пожалуйста, дождитесь ответа.")
        elif query.data == "start_info":
            return start_info(update, context)
        elif query.data == "author":
            return how_to_become_author(update, context)
        elif query.data == "platform_info":
            return platform_info(update, context)
        elif query.data == "test_mission":
            return test_mission(update, context)
        elif query.data in ["mission_correct", "mission_incorrect"]:
            return handle_mission_response(update, context)
        elif query.data == "continue_education":
            return continue_education(update, context)
        elif query.data == "test_roles":
            return test_roles(update, context)
        elif query.data in ["roles_correct", "roles_incorrect"]:
            return handle_roles_response(update, context)
        elif query.data == "test_karma":
            return test_karma(update, context)
        elif query.data in ["karma_correct", "karma_incorrect"]:
            return handle_karma_response(update, context)
        elif query.data == "final_video":
            return final_video(update, context)
        elif query.data == "final_test":
            return final_test(update, context)
        elif query.data in ["final_correct", "final_incorrect"]:
            return handle_final_test_response(update, context)
        elif query.data == "first_block_done":
            return first_block_done(update, context)
        elif query.data == "start_now_1":
            return start_second_block(update, context)
        elif query.data == "start_now_2":
            return second_block_2(update, context)
        elif query.data == "quiz_policy":
            return quiz_policy(update, context)
        elif query.data in ["policy_correct", "policy_wrong"]:
            return quiz_facts(update, context)
        elif query.data == "quiz_facts":
            return pre_quiz_beautiful(update, context)
        elif query.data == "quiz_beautiful":
            return quiz_beautiful(update, context)
        elif query.data in ["beauty_correct", "beauty_wrong"]:
            return handle_beautiful_response(update, context)
        elif query.data in ["krasivo_correct", "krasivo_wrong"]:
            return handle_quiz_completion(update, context)
        elif query.data == "quiz_complete":
            return second_block_pre_final(update, context)
        elif query.data == "policy_learned":
            return second_block_final(update, context)
        elif query.data == "take_break":
            return take_break(update, context)
        elif query.data == "start_now_second":
            return start_training(update, context)
        elif query.data == "test_video":
            return test_video(update, context)
        elif query.data in ["video_correct", "video_wrong"]:
            return handle_test_video_response(update, context)
        elif query.data == "video_continue_education":
            return video_continue_education(update, context)
        elif query.data == "test_block":
            return test_block(update, context)
        elif query.data in ["plan_correct", "plan_wrong"]:
            return handle_test_block_response(update, context)
        elif query.data == "third_block_continue":
            return third_block_pre_final(update, context)
        elif query.data == "third_block_final":
            return third_block_final(update, context)
        elif query.data == "start_now_third":
            return start_fourh_block(update, context)
        elif query.data == "test_rules":
            return test_rules(update, context)
        elif query.data in ["rules_correct", "rules_wrong"]:
            return handle_test_rules_response(update, context)
        elif query.data == "test_guideline":
            return test_guideline(update, context)
        elif query.data in ["guid_correct", "guid_wrong"]:
            return handle_test_guideline_response(update, context)
        elif query.data == "continue_fourh_block":
            return continue_fourh_block(update, context)
        elif query.data == "fourh_block_final":
            return fourh_block_final(update, context)
        elif query.data == "test_distribution":
            return test_distribution(update, context)
        elif query.data == "fourh_block_final":
            return fourh_block_final(update, context)
        elif query.data == "start_now_fourh":
            return start_fifth_block(update, context)
        elif query.data in ["dis_correct", "dis_wrong"]:
            return handle_test_distribution_response(update, context)
        elif query.data == "distribution_overview":
            return distribution_overview(update, context)
        elif query.data == "pre_test_next":
            return pre_next_test(update, context)
        elif query.data == "test_next":
            return test_next(update, context)
        elif query.data in ["next_correct", "next_wrong"]:
            return handle_test_next_response(update, context)
        elif query.data == "analyze_cases":
            return analyze_cases(update, context)
        elif query.data in ["yes", "no", "maybe"]:
            return get_author_decision(update, context)
        else:
            query.message.reply_text("Неизвестная команда.")
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
    finally:
        query.answer()  # Убедитесь, что query.answer вызывается в любом случае


def handle_message(update: Update, context: CallbackContext):
    try:
        # Запись сообщения пользователя в базу данных
        with sqlite3.connect('playground_bot.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO messages (chat_id, message, sender) VALUES (?, ?, ?)", 
                           (update.message.from_user.id, update.message.text, 'user'))
            conn.commit()
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")

def main():
    # Создаем Updater и передаем ему токен вашего бота
    updater = Updater(API_TOKEN)
    
    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # Создаем обработчик для диалогов
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FIRST_NAME: [MessageHandler(Filters.text & ~Filters.command, first_name)],
            LAST_NAME: [MessageHandler(Filters.text & ~Filters.command, last_name)],
            CITY: [MessageHandler(Filters.text & ~Filters.command, city)],
            INTERESTS: [MessageHandler(Filters.text & ~Filters.command, interests)],
            AGE: [CallbackQueryHandler(age, pattern='^age_')],
            HOW_TO_BECOME_AUTHOR: [CallbackQueryHandler(how_to_become_author, pattern='^author$')],
            START_NOW: [CallbackQueryHandler(start_education, pattern='^start_now$')],
            START_LATER: [CallbackQueryHandler(start_later, pattern='^start_later$')],
            PLATFORM_INFO: [CallbackQueryHandler(platform_info, pattern='^platform_info$')],
            MISSION: [CallbackQueryHandler(test_mission, pattern='test_mission')],
            KARMA: [
                CallbackQueryHandler(handle_mission_response, pattern='mission_correct'),
                CallbackQueryHandler(handle_mission_response, pattern='mission_incorrect'),
                CallbackQueryHandler(continue_education, pattern='continue_education'),
                CallbackQueryHandler(handle_roles_response, pattern='roles_correct'),
                CallbackQueryHandler(handle_roles_response, pattern='roles_incorrect'),
                CallbackQueryHandler(handle_karma_response, pattern='karma_correct'),
                CallbackQueryHandler(handle_karma_response, pattern='karma_incorrect'),
                CallbackQueryHandler(final_video, pattern='final_video'),
                CallbackQueryHandler(final_test, pattern='final_test')
            ],
            FINAL_VIDEO: [CallbackQueryHandler(handle_karma_response, pattern='karma_correct')],
            FINAL_TEST: [CallbackQueryHandler(handle_final_test_response, pattern='final_correct')],
            FIRST_BLOCK_DONE: [CallbackQueryHandler(first_block_done, pattern='first_block_done')],
            # FIRST_QUESTION: [MessageHandler(Filters.text & ~Filters.command, first_question)],  # Ожидание ответа на первый вопрос
            # SECOND_BLOCK: [CallbackQueryHandler(start_second_block, pattern='start_now_2')],
            # TEST: [CallbackQueryHandler(pass_test, pattern='pass_test')],
            # NEXT_TEST_QUESTION: [CallbackQueryHandler(handle_test_answer, pattern='correct_1|wrong_1|wrong_2')]
        },
        fallbacks=[CallbackQueryHandler(start_later, pattern='start_later')],
    )
    second_third_block_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_second_block, pattern='^start_now_1$')],
        states={
            FIRST_QUESTION: [MessageHandler(Filters.text & ~Filters.command, first_question)],
            QUIZ_POLICY: [CallbackQueryHandler(quiz_policy, pattern="quiz_policy")],
            QUIZ_FACTS: [CallbackQueryHandler(quiz_facts, pattern="quiz_facts")],
            QUIZ_BEAUTIFUL: [CallbackQueryHandler(handle_beautiful_response, pattern="quiz_beautiful")],
            START_TRAINING: [CallbackQueryHandler(start_training, pattern='start_training')],
            TEST_VIDEO: [
                CallbackQueryHandler(test_video, pattern='test_video'),
                CallbackQueryHandler(handle_test_video_response)
            ],
            CONTINUE_EDUCATION: [CallbackQueryHandler(continue_education, pattern='continue_education')],
            TEST_BLOCK: [
                CallbackQueryHandler(test_block, pattern='test_block'),
                CallbackQueryHandler(handle_test_block_response)
            ],
            START_FOURH_BLOCK: [
                CallbackQueryHandler(start_training, pattern='^start_training$')
            ],
            TEST_RULES: [
                CallbackQueryHandler(test_rules, pattern='^test_rules$'),
                CallbackQueryHandler(handle_test_rules_response)
            ],
            CONTINUE_FOURH_BLOCK: [
                CallbackQueryHandler(continue_education, pattern='^continue_education$')
            ],
            TEST_GUIDELINE: [
                CallbackQueryHandler(test_guideline, pattern='^test_guideline$'),
                CallbackQueryHandler(handle_test_guideline_response)
            ],
            START_FIFTH_BLOCK: [
                CallbackQueryHandler(start_training, pattern='^start_training$')
            ],
            TEST_DISTRIBUTION: [
                CallbackQueryHandler(test_distribution, pattern='^test_distribution$'),
                CallbackQueryHandler(handle_test_distribution_response)
            ],
            DISTRIBUTION_OVERVIEW: [
                CallbackQueryHandler(distribution_overview, pattern='^distribution_overview$')
            ],
            TEST_NEXT: [
                CallbackQueryHandler(test_next, pattern='^test_next$'),
                CallbackQueryHandler(handle_test_next_response)
            ],
            ANALYZE_CASES: [
                CallbackQueryHandler(analyze_cases, pattern='^analyze_cases$')
            ],
            START_FEEDBACK: [MessageHandler(Filters.text & ~Filters.command, start_feedback)]
        },
        fallbacks=[],
    )
    final_handler = ConversationHandler(
        entry_points=[CommandHandler('start_feedback', start_feedback)],
        states={
            GET_USEFUL_INFO: [MessageHandler(Filters.text & ~Filters.command, get_useful_info)],
            GET_USELESS_INFO: [MessageHandler(Filters.text & ~Filters.command, get_useless_info)],
            GET_WANTED_INFO: [MessageHandler(Filters.text & ~Filters.command, get_wanted_info)],
            GET_AUTHOR_DECISION: [CallbackQueryHandler(get_author_decision)],
            GET_FINAL_FEEDBACK: [MessageHandler(Filters.text & ~Filters.command, get_final_feedback)],
        },
        fallbacks=[CommandHandler('start_feedback', start_feedback)],
    )
    # Добавляем обработчики в диспетчер
    dp.add_handler(conv_handler)  # Обработчик для диалогов
    dp.add_handler(second_third_block_handler)
    dp.add_handler(final_handler)
    dp.add_handler(CallbackQueryHandler(handle_callback))  # Обработчик для callback-запросов
    dp.add_handler(CommandHandler('menu', menu))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    # Начинаем опрос обновлений от Telegram
    updater.start_polling()

    # Ожидаем завершения работы бота
    updater.idle()

if __name__ == '__main__':
    init_db()
    populate_initial_data()
    main()