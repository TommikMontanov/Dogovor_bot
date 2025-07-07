import os
import threading
import time
import http.client
import http.server
import socketserver
import json
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from io import BytesIO
from create_docs import generate_excel_and_docx  # импорт генерации Excel и DOCX

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Переменные окружения
API_TOKEN = os.getenv('API_TOKEN')
SELF_URL = os.getenv('SELF_URL', 'https://dogovor-bot-5q8p.onrender.com')  # Замените на ваш URL Render
PORT = int(os.getenv('PORT', 8000))  # Render задает PORT, по умолчанию 8000 для локального тестирования

user_states = {}

# Простой HTTP-сервер для ответа на запросы
class PingHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')

# Функция пинга
def heartbeat():
    while True:
        try:
            host = SELF_URL.replace('https://', '')
            conn = http.client.HTTPSConnection(host)
            conn.request('GET', '/')
            res = conn.getresponse()
            logging.info(f'[Пинг] Код статуса: {res.status}')
            conn.close()
        except Exception as e:
            logging.error(f'[Пинг] Ошибка: {str(e)}')
        time.sleep(30)  # Пинг каждые 30 секунд

# Запуск пинга в отдельном потоке
def start_heartbeat():
    heartbeat_thread = threading.Thread(target=heartbeat)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()
    logging.info('Пинг запущен')

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Начать", callback_data='start_process')]]
    )
    await update.message.reply_text("Нажмите кнопку, чтобы начать", reply_markup=keyboard)

# Кнопка "Начать"
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_states[user_id] = {"awaiting_image": True}
    await context.bot.send_message(chat_id=user_id, text="Пожалуйста, отправьте изображение.")

# Обработка фото
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not user_states.get(user_id, {}).get("awaiting_image"):
        return

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = BytesIO()
    await file.download_to_memory(out=image_bytes)
    image_bytes.seek(0)

    text = (
        "Ты должен получить данные из фото и дать мне пример в таком виде:\n"
        "[\n"
        "  {\"id\": \"2.4\", \"размер\": \"780x700\", \"кол-во\": 25, \"цена\": 230000},\n"
        "  {\"id\": \"2.1\", \"размер\": \"780x700\", \"кол-во\": 2, \"цена\": 230000},\n"
        "  {\"id\": \"2.4\", \"размер\": \"1000x900\", \"кол-во\": 5, \"цена\": 360000}\n"
        "]"
    )

    await context.bot.send_photo(
        chat_id=user_id,
        photo=image_bytes,
        caption=text
    )

    user_states[user_id] = {"awaiting_json": True}

# Обработка JSON от пользователя
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not user_states.get(user_id, {}).get("awaiting_json"):
        return

    try:
        # Чтение и очистка текста
        message_text = update.message.text.replace('\u00A0', ' ')  # убираем неразрывные пробелы
        message_text = re.sub(r'[ \t]+', ' ', message_text).strip()  # убираем лишние пробелы и табуляции

        # Убираем обёртки ```
        if message_text.startswith('```') and message_text.endswith('```'):
            message_text = '\n'.join(message_text.split('\n')[1:-1]).strip()

        # Парсинг JSON
        data = json.loads(message_text)

        if not isinstance(data, list):
            raise ValueError("Ожидается список объектов.")

        # Проверка ключей
        required_keys = {'id', 'размер', 'кол-во', 'цена'}
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"Элемент #{i + 1} не является объектом.")
            missing = required_keys - item.keys()
            if missing:
                raise ValueError(f"В элементе #{i + 1} отсутствуют ключи: {', '.join(missing)}")

        # Генерация Excel и DOCX
        excel_bytes, docx_bytes = generate_excel_and_docx(data)

        await context.bot.send_document(chat_id=user_id, document=InputFile(excel_bytes, filename="таблица.xlsx"))
        await context.bot.send_document(chat_id=user_id, document=InputFile(docx_bytes, filename="договор.docx"))

        await update.message.reply_text("✅ Готово! Нажмите /start, чтобы начать заново.")
        user_states.pop(user_id, None)

    except json.JSONDecodeError as e:
        logging.error("Ошибка JSON: %s", e)
        await update.message.reply_text(
            "❌ Ошибка в формате JSON.\n"
            "Проверьте правильность кавычек, запятых и структуры.\n"
            "Пример:\n"
            '[{"id": "2.4", "размер": "780x700", "кол-во": 25, "цена": 230000}]'
        )
    except Exception as e:
        logging.error("Ошибка обработки JSON:", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {e}")

# Запуск бота
def main():
    # Проверка \

API_TOKEN
    if not API_TOKEN:
        logging.error("API_TOKEN не установлен. Проверьте переменные окружения.")
        return

    # Запуск HTTP-сервера в отдельном потоке
    server = socketserver.TCPServer(('', PORT), PingHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    logging.info(f'HTTP-сервер запущен на порту {PORT}')

    # Запуск пинга
    start_heartbeat()

    # Запуск бота
    app = ApplicationBuilder().token(API_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    try:
        app.run_polling()
    finally:
        server.shutdown()
        server.server_close()
        logging.info('HTTP-сервер остановлен')

if __name__ == "__main__":
    main()
