from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import logging
import os
from werkzeug.utils import secure_filename
import pandas as pd
from telegram import Bot
from init_db import move_data
from config import API_TOKEN
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'supersecretkey'

logging.basicConfig(level=logging.INFO)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Настройка SocketIO
socketio = SocketIO(app)


# Создайте экземпляр бота
bot = Bot(token=API_TOKEN)

def get_bot_texts():
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bot_texts")
    texts = cursor.fetchall()
    conn.close()
    return texts

def get_db_connection():
    conn = sqlite3.connect('playground_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_contact_requests():
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT contact_requests.chat_id, users.username, contact_requests.timestamp FROM contact_requests LEFT JOIN users ON contact_requests.chat_id = users.chat_id")
    requests = cursor.fetchall()
    conn.close()
    return [{"chat_id": r[0], "username": r[1], "timestamp": r[2]} for r in requests]

def get_messages(chat_id):
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT message, sender, timestamp FROM messages WHERE chat_id = ? ORDER BY timestamp", (chat_id,))
    messages = cursor.fetchall()
    conn.close()
    return [{"message": m[0], "sender": m[1], "timestamp": m[2]} for m in messages]

@app.route('/get_messages', methods=['GET'])
def get_messages_ajax():
    chat_id = request.args.get('chat_id')
    messages = get_messages(chat_id)
    return render_template('messages.html', messages=messages)

@app.route("/", methods=["GET"])
def index():
    chat_id = request.args.get("chat_id")
    contact_requests = get_contact_requests()
    messages = get_messages(chat_id) if chat_id else None
    return render_template("index.html", contact_requests=contact_requests, messages=messages, chat_id=chat_id)

@app.route("/send_message", methods=["POST"])
def send_message():
    chat_id = request.form.get("chat_id")
    message = request.form.get("message")

    if chat_id and message:
        try:
            conn = sqlite3.connect('playground_bot.db')
            cursor = conn.cursor()

            # Вставка запроса в таблицу contact_requests с уникальностью chat_id
            try:
                cursor.execute('''
                    INSERT INTO contact_requests (chat_id)
                    VALUES (?)
                ''', (chat_id,))
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # Запись уже существует, игнорируем

            # Запись сообщения в базу данных
            cursor.execute("INSERT INTO messages (chat_id, message, sender) VALUES (?, ?, ?)", 
                           (chat_id, message, 'admin'))
            conn.commit()
            conn.close()

            # Отправка сообщения пользователю через синхронного бота
            bot.send_message(chat_id, message)

            flash("Message sent successfully!")
            
            # Отправляем сообщение на клиент через веб-сокеты
            socketio.emit('new_message', {'chat_id': chat_id, 'message': message, 'sender': 'admin'})

        except Exception as e:
            logging.error(f"Error sending message: {e}")
            flash("Failed to send message.")
    else:
        flash("Chat ID or message is missing.")

    return redirect(url_for('index', chat_id=chat_id))

@app.route('/export', methods=['GET', 'POST'])
def export_contacts():
    if request.method == 'POST':
        try:
            conn = sqlite3.connect('playground_bot.db')
            df = pd.read_sql_query("SELECT * FROM users", conn)
            file_path = os.path.join('static', 'contacts_export.xlsx')
            df.to_excel(file_path, index=False)
            conn.close()
            return render_template('export.html', download_link=file_path)
        except Exception as e:
            logging.error(f"Error exporting contacts: {e}")
            flash("Ошибка при выгрузке контактов.")
            return redirect(url_for('index'))
    return render_template('export.html')

@app.route('/send', methods=['GET', 'POST'])
def send_message_to_all():
    if request.method == 'POST':
        text = request.form['message']
        category_id = request.form.get('category_id')

        try:
            conn = sqlite3.connect('playground_bot.db')
            cursor = conn.cursor()
            
            if category_id:
                cursor.execute("""
                    SELECT users.chat_id 
                    FROM users 
                    JOIN user_categories ON users.chat_id = user_categories.user_id 
                    WHERE user_categories.category_id = ?
                """, (category_id,))
            else:
                cursor.execute("SELECT chat_id FROM users")
                
            chat_ids = cursor.fetchall()
            conn.close()

            for chat_id in chat_ids:
                try:
                    bot.send_message(chat_id[0], text)
                except Exception as e:
                    logging.error(f"Failed to send message to chat_id {chat_id[0]}: {e}")

            flash("Сообщение отправлено пользователям.")
            return redirect(url_for('index'))
        except Exception as e:
            logging.error(f"Error in send_message: {e}")
            flash("Ошибка при отправке сообщения.")
            return redirect(url_for('index'))
    else:
        categories = get_categories()
        return render_template('send.html', categories=categories)

@app.route('/add', methods=['GET', 'POST'])
def add_menu_item():
    if request.method == 'POST':
        label = request.form['label']
        callback_data = request.form['callback_data']
        response_type = request.form['response_type']
        response_content = request.form['response_content']

        try:
            conn = sqlite3.connect('playground_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO menu_items (label, callback_data, response_type, response_content)
                VALUES (?, ?, ?, ?)
            ''', (label, callback_data, response_type, response_content))
            conn.commit()
            conn.close()
            flash("Элемент меню добавлен.")
            return redirect(url_for('index'))
        except Exception as e:
            logging.error(f"Error adding menu item: {e}")
            flash("Ошибка при добавлении элемента меню.")
            return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_menu_item(item_id):
    if request.method == 'POST':
        label = request.form['label']
        callback_data = request.form['callback_data']
        response_type = request.form['response_type']
        response_content = request.form['response_content']

        try:
            conn = sqlite3.connect('playground_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE menu_items
                SET label = ?, callback_data = ?, response_type = ?, response_content = ?
                WHERE id = ?
            ''', (label, callback_data, response_type, response_content, item_id))
            conn.commit()
            conn.close()
            flash("Элемент меню обновлен.")
            return redirect(url_for('index'))
        except Exception as e:
            logging.error(f"Error updating menu item: {e}")
            flash("Ошибка при обновлении элемента меню.")
            return redirect(url_for('index'))
    else:
        conn = sqlite3.connect('playground_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM menu_items WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        conn.close()
        return render_template('edit.html', item=item)

@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_menu_item(item_id):
    try:
        conn = sqlite3.connect('playground_bot.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        flash("Элемент меню удален.")
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error deleting menu item: {e}")
        flash("Ошибка при удалении элемента меню.")
        return redirect(url_for('index'))

@app.route('/texts')
def texts():
    bot_texts = get_bot_texts()
    return render_template('texts.html', bot_texts=bot_texts)

@app.route('/add_text', methods=['GET', 'POST'])
def add_text():
    if request.method == 'POST':
        key = request.form['key']
        content = request.form['content']

        try:
            conn = sqlite3.connect('playground_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bot_texts (key, content)
                VALUES (?, ?)
            ''', (key, content))
            conn.commit()
            conn.close()
            flash("Текст добавлен.")
            return redirect(url_for('texts'))
        except Exception as e:
            logging.error(f"Error adding text: {e}")
            flash("Ошибка при добавлении текста.")
            return redirect(url_for('texts'))
    return render_template('add_text.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/edit_text/<int:text_id>', methods=['GET', 'POST'])
def edit_text(text_id):
    if request.method == 'POST':
        key = request.form['key']
        content = request.form['content']
        uploaded_file = request.files['file']

        # Если файл был загружен, сохраняем его
        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(file_path)

            # Добавляем информацию о файле в базу данных
            conn = sqlite3.connect('playground_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO bot_files (bot_text_key, file_name, file_type)
                VALUES (?, ?, ?)
            ''', (key, filename, uploaded_file.mimetype.split('/')[0]))  # file_type: 'video', 'image', etc.
            conn.commit()
            conn.close()

        try:
            conn = sqlite3.connect('playground_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE bot_texts
                SET key = ?, content = ?
                WHERE id = ?
            ''', (key, content, text_id))
            conn.commit()
            conn.close()
            flash("Текст обновлен.")
            return redirect(url_for('texts'))
        except Exception as e:
            logging.error(f"Error updating text: {e}")
            flash("Ошибка при обновлении текста.")
            return redirect(url_for('texts'))
    else:
        conn = sqlite3.connect('playground_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bot_texts WHERE id = ?", (text_id,))
        text = cursor.fetchone()
        conn.close()
        return render_template('edit_text.html', text=text)


@app.route('/delete_text/<int:text_id>', methods=['POST'])
def delete_text(text_id):
    try:
        conn = sqlite3.connect('playground_bot.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bot_texts WHERE id = ?", (text_id,))
        conn.commit()
        conn.close()
        flash("Текст удален.")
        return redirect(url_for('texts'))
    except Exception as e:
        logging.error(f"Error deleting text: {e}")
        flash("Ошибка при удалении текста.")
        return redirect(url_for('texts'))
    
def get_categories():
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories")
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_users():
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, username FROM users")
    users = cursor.fetchall()
    conn.close()
    return [{'chat_id': row[0], 'username': row[1]} for row in users]

def get_user_category(chat_id):
    conn = sqlite3.connect('playground_bot.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT categories.name 
        FROM user_categories 
        JOIN categories ON user_categories.category_id = categories.id 
        WHERE user_categories.user_id = ?
    """, (chat_id,))
    category = cursor.fetchone()
    conn.close()
    return category[0] if category else None

@app.route("/moderate", methods=["GET", "POST"])
def moderate():
    if request.method == "POST":
        chat_id = request.form.get("chat_id")
        category_id = request.form.get("category_id")

        if not chat_id or not category_id:
            flash("Chat ID or Category ID is missing.")
            return redirect(url_for('moderate'))

        try:
            conn = sqlite3.connect('playground_bot.db')
            cursor = conn.cursor()

            # Удаление текущей категории пользователя, если она существует
            cursor.execute("DELETE FROM user_categories WHERE user_id = ?", (chat_id,))

            # Добавление новой категории
            cursor.execute("INSERT INTO user_categories (user_id, category_id) VALUES (?, ?)", (chat_id, category_id))
            conn.commit()
            conn.close()
            flash("Категория обновлена.")
        except Exception as e:
            logging.error(f"Error updating category: {e}")
            flash("Ошибка при обновлении категории.")
        return redirect(url_for('moderate'))

    # Получение всех пользователей и категорий
    users = get_users()
    categories = get_categories()

    user_categories = {}
    for user in users:
        user_id = user['chat_id']
        category = get_user_category(user_id)
        user_categories[user_id] = category

    return render_template("moderate.html", users=users, categories=categories, user_categories=user_categories)



@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        name = request.form['name']

        if name:
            try:
                conn = sqlite3.connect('playground_bot.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO categories (name)
                    VALUES (?)
                ''', (name,))
                conn.commit()
                conn.close()
                flash("Категория успешно добавлена.")
                return redirect(url_for('manage_users'))
            except Exception as e:
                logging.error(f"Ошибка при добавлении категории: {e}")
                flash("Ошибка при добавлении категории.")
        else:
            flash("Название категории не должно быть пустым.")
    
    return render_template('add_category.html')


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)
