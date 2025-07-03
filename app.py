import os
import threading
import time
import http.client
import json
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from io import BytesIO
from create_docs import generate_excel_and_docx  # импорт генерации Excel и DOCX

API_TOKEN = os.getenv('API_TOKEN')

logging.basicConfig(level=logging.INFO)
user_states = {}

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
        caption=text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Переслать другим", switch_inline_query="")]]
        )
    )

    user_states[user_id] = {"awaiting_json": True}

# Обработка JSON от пользователя
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not user_states.get(user_id, {}).get("awaiting_json"):
        return

    try:
        data = json.loads(update.message.text)
        if not isinstance(data, list):
            raise ValueError

        # Генерация файлов
        excel_bytes, docx_bytes = generate_excel_and_docx(data)

        await context.bot.send_document(chat_id=user_id, document=InputFile(excel_bytes, filename="таблица.xlsx"))
        await context.bot.send_document(chat_id=user_id, document=InputFile(docx_bytes, filename="договор.docx"))

        await update.message.reply_text("✅ Готово! Нажмите /start, чтобы начать заново.")
        user_states.pop(user_id, None)

    except Exception as e:
        logging.error("Ошибка при обработке JSON:", exc_info=True)
        await update.message.reply_text("❌ Ошибка в формате JSON. Отправьте корректные данные.")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# URL приложения на Render
SELF_URL = os.getenv('SELF_URL', 'https://dogovor-bot-gzdq.onrender.com')  # Замените на ваш URL Render

# Функция пинга
def heartbeat():
    while True:
        try:
            # Удаляем 'https://' из URL для http.client
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


# Запуск бота
def main():
    app = ApplicationBuilder().token(API_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
