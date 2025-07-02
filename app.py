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

API_TOKEN = '7604612037:AAHdcVbG7YGMFmkWCxJ-yh7w8g8ECukAZrA'

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
























# import pandas as pd
# from openpyxl import load_workbook
# from openpyxl.styles import Font, Alignment, Border, Side
# from openpyxl.utils import get_column_letter
# from docx import Document
# from docx.shared import Pt
# from docx.enum.text import WD_ALIGN_PARAGRAPH
# from datetime import datetime

# # ✅ Данные
# data = [
#     {"id": "2.4", "размер": "780x700", "кол-во": 25, "цена": 230000},
#     {"id": "2.1", "размер": "780x700", "кол-во": 2, "цена": 230000},
#     {"id": "2.4", "размер": "1000x900", "кол-во": 5, "цена": 360000},
# ]

# # ✅ Сбор таблицы
# rows = []
# for i, item in enumerate(data, 2):
#     rows.append({
#         "№": i - 1,
#         "Наименование": f"Дорожный знак,{item['id']},размер {item['размер']}",
#         "Ед. изм": "шт",
#         "Кол-во": item["кол-во"],
#         "Цена": item["цена"],
#         "Стоимость поставки": "",
#         "НДС ставка": "12%",
#         "НДС сумма": "",
#         "Всего сумма с НДС": ""
#     })

# df = pd.DataFrame(rows)

# # ✅ Добавляем строку ИТОГО
# last_row_excel = len(df) + 2
# df.loc[len(df.index)] = {
#     "№": "ИТОГО:",
#     "Наименование": "",
#     "Ед. изм": "",
#     "Кол-во": f"=SUM(D2:D{last_row_excel - 1})",
#     "Цена": "",
#     "Стоимость поставки": f"=SUM(F2:F{last_row_excel - 1})",
#     "НДС ставка": "",
#     "НДС сумма": f"=SUM(H2:H{last_row_excel - 1})",
#     "Всего сумма с НДС": f"=SUM(I2:I{last_row_excel - 1})"
# }

# # ✅ Сохраняем Excel
# excel_filename = "результат_с_формулами.xlsx"
# df.to_excel(excel_filename, index=False)

# # ✅ Форматируем Excel
# wb = load_workbook(excel_filename)
# ws = wb.active

# for i in range(2, last_row_excel):
#     ws[f"F{i}"] = f"=D{i}*E{i}"
#     ws[f"H{i}"] = f"=F{i}*0.12"
#     ws[f"I{i}"] = f"=F{i}+H{i}"

# thin = Side(style="thin")
# thick = Side(style="thick")
# thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)
# thick_border = Border(left=thick, right=thick, top=thick, bottom=thick)

# for row in ws.iter_rows():
#     for cell in row:
#         row_idx = cell.row
#         cell.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
#         cell.font = Font(name="Arial", size=10, bold=(row_idx == 1 or row_idx == last_row_excel))
#         cell.border = thick_border if row_idx in [1, last_row_excel] else thin_border

# # ✅ Автоширина
# for col in ws.columns:
#     max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
#     ws.column_dimensions[col[0].column_letter].width = max_len + 2

# # ✅ Высота строк
# for row in ws.iter_rows():
#     for cell in row:
#         if cell.column_letter == "B":
#             ws.row_dimensions[cell.row].height = 30

# wb.save(excel_filename)
# print(f"✅ Excel-файл сохранён: {excel_filename}")

# # ✅ DOCX
# total_qty = sum(item["кол-во"] for item in data)
# total_cost = sum(item["кол-во"] * item["цена"] for item in data)
# nds = int(total_cost * 0.12)
# total_with_nds = total_cost + nds

# # ✅ Функция суммы прописью
# def num_to_words(number):
#     try:
#         from num2words import num2words
#         return num2words(number, lang='ru').capitalize()
#     except:
#         return f"{number:,.2f}".replace(",", " ").replace(".", ",")

# # ✅ Даты
# today = datetime.now()
# today_str = today.strftime("%d/%m")
# date_for_contract = f"«{today.day}» {today.strftime('%B')} {today.year}г."

# doc = Document()
# style = doc.styles['Normal']
# style.font.name = 'Arial'
# style.font.size = Pt(11)

# doc.add_paragraph(f"Договор-счет №   {today_str} на выполнение работ и услуг").alignment = WD_ALIGN_PARAGRAPH.CENTER
# doc.add_paragraph("г. Ташкент\t\t\t\t\t" + date_for_contract)

# doc.add_paragraph(
#     'OOО «NUR  FAYZ  REKLAMA», именуемый в дальнейшем «Исполнитель», в лице директора Файзиева Н.С., '
#     'действующий на основании Устава, с одной стороны, и "HIGH CITY-DEVELOPERS" MCHJ, именуемый в дальнейшем '
#     '«Заказчик», в лице директора __________, действующего на основании Устава, с другой стороны, заключили настоящий Договор о нижеследующем:'
# )

# doc.add_paragraph("1. ПРЕДМЕТ ДОГОВОРА")
# doc.add_paragraph(
#     "1.1. Исполнитель обязуется изготовить продукцию и прочие услуги, а Заказчик обязуется оплатить и принять на условиях, "
#     "установленных настоящим Договором согласно следующей спецификации:"
# )

# # ✅ Таблица
# table = doc.add_table(rows=1, cols=9)
# table.style = 'Table Grid'
# headers = ["№", "Наименование", "Ед. изм", "Кол-во", "Цена", "Стоимость поставки", "НДС ставка", "НДС сумма", "Всего сумма с НДС"]
# for i, h in enumerate(headers):
#     table.rows[0].cells[i].text = h

# for i, item in enumerate(data, 1):
#     qty = item["кол-во"]
#     price = item["цена"]
#     cost = qty * price
#     vat = int(cost * 0.12)
#     total = cost + vat
#     row_cells = table.add_row().cells
#     row_cells[0].text = str(i)
#     row_cells[1].text = f"Дорожный знак {item['id']}, размер {item['размер']}"
#     row_cells[2].text = "шт"
#     row_cells[3].text = str(qty)
#     row_cells[4].text = f"{price:,.2f}".replace(",", " ").replace(".", ",")
#     row_cells[5].text = f"{cost:,.2f}".replace(",", " ").replace(".", ",")
#     row_cells[6].text = "12%"
#     row_cells[7].text = f"{vat:,.2f}".replace(",", " ").replace(".", ",")
#     row_cells[8].text = f"{total:,.2f}".replace(",", " ").replace(".", ",")

# # ✅ ИТОГО
# row_cells = table.add_row().cells
# row_cells[0].text = "ИТОГО:"
# row_cells[3].text = str(total_qty)
# row_cells[5].text = f"{total_cost:,.2f}".replace(",", " ").replace(".", ",")
# row_cells[7].text = f"{nds:,.2f}".replace(",", " ").replace(".", ",")
# row_cells[8].text = f"{total_with_nds:,.2f}".replace(",", " ").replace(".", ",")

# doc.add_paragraph(
#     f"2. ОБЩАЯ СУММА И ПОРЯДОК ОПЛАТЫ\n"
#     f"2.1. Общая сумма настоящего Договора составляет: {total_with_nds:,.2f} "
#     f"({num_to_words(total_with_nds)} сумов 00 тийин), с учетом НДС."
# )

# # ✅ Сохраняем
# doc_filename = "договор.docx"
# doc.save(doc_filename)
# print(f"✅ DOCX-файл сохранён: {doc_filename}")















# import ast
# import pandas as pd
# from io import BytesIO
# from openpyxl import load_workbook
# from openpyxl.styles import Font, Alignment, Border, Side
# from telegram import (
#     InlineKeyboardButton,
#     InlineKeyboardMarkup,
#     Update,
#     InputFile
# )
# from telegram.ext import (
#     ApplicationBuilder,
#     CommandHandler,
#     MessageHandler,
#     CallbackQueryHandler,
#     ContextTypes,
#     filters
# )

# # Токен от BotFather
# BOT_TOKEN = "7604612037:AAHdcVbG7YGMFmkWCxJ-yh7w8g8ECukAZrA"  # ← замени на свой

# # Стили границ
# thin_border = Border(
#     left=Side(style='thin'), right=Side(style='thin'),
#     top=Side(style='thin'), bottom=Side(style='thin')
# )
# thick_border = Border(
#     left=Side(style='thick'), right=Side(style='thick'),
#     top=Side(style='thick'), bottom=Side(style='thick')
# )

# # Команда /start
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     keyboard = [[InlineKeyboardButton("Start", callback_data='start_process')]]
#     await update.message.reply_text("Нажмите кнопку Start, чтобы начать", reply_markup=InlineKeyboardMarkup(keyboard))

# # Обработка callback кнопок
# async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()
#     if query.data == 'start_process':
#         await query.message.reply_text("Пожалуйста, отправьте изображение, с которого нужно считать данные.")

# # Обработка изображения
# async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     photo = update.message.photo[-1]
#     file = await context.bot.get_file(photo.file_id)
#     image_bytes = await file.download_as_bytearray()

#     caption = (
#         "Ты должен получить данные из фото и дать мне пример в таком виде:\n\n"
#         "[\n"
#         "    {\"id\": \"2.4\", \"размер\": \"780x700\", \"кол-во\": 25, \"цена\": 230000},\n"
#         "    {\"id\": \"2.1\", \"размер\": \"780x700\", \"кол-во\": 2, \"цена\": 230000},\n"
#         "    {\"id\": \"2.4\", \"размер\": \"1000x900\", \"кол-во\": 5, \"цена\": 360000}\n"
#         "]"
#     )

#     keyboard = [[InlineKeyboardButton("Переслать другим", switch_inline_query=caption)]]
#     await update.message.reply_photo(photo=BytesIO(image_bytes), caption=caption, reply_markup=InlineKeyboardMarkup(keyboard))

# # Обработка JSON-текста и генерация Excel
# async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     try:
#         text = update.message.text
#         data = ast.literal_eval(text)

#         if not isinstance(data, list) or not all(isinstance(d, dict) for d in data):
#             raise ValueError("Неверный формат данных")

#         rows = []
#         for i, item in enumerate(data, 2):
#             rows.append({
#                 "№": i - 1,
#                 "Наименование": f"Дорожный знак,{item['id']},размер {item['размер']}",
#                 "Ед. изм": "шт",
#                 "Кол-во": item["кол-во"],
#                 "Цена": item["цена"],
#                 "Стоимость поставки": "",
#                 "НДС ставка": "12%",
#                 "НДС сумма": "",
#                 "Всего сумма с НДС": ""
#             })

#         df = pd.DataFrame(rows)
#         last_row = len(df) + 2

#         df.loc[len(df.index)] = {
#             "№": "ИТОГО:",
#             "Наименование": "",
#             "Ед. изм": "",
#             "Кол-во": f"=SUM(D2:D{last_row - 1})",
#             "Цена": "",
#             "Стоимость поставки": f"=SUM(F2:F{last_row - 1})",
#             "НДС ставка": "",
#             "НДС сумма": f"=SUM(H2:H{last_row - 1})",
#             "Всего сумма с НДС": f"=SUM(I2:I{last_row - 1})"
#         }

#         buffer = BytesIO()
#         df.to_excel(buffer, index=False)
#         buffer.seek(0)

#         wb = load_workbook(buffer)
#         ws = wb.active

#         for i in range(2, last_row):
#             ws[f"F{i}"] = f"=D{i}*E{i}"
#             ws[f"H{i}"] = f"=F{i}*0.12"
#             ws[f"I{i}"] = f"=F{i}+H{i}"

#         for row in ws.iter_rows():
#             for cell in row:
#                 r = cell.row
#                 cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
#                 cell.font = Font(name="Arial", size=10)
#                 cell.border = thick_border if r == 1 or r == last_row else thin_border

#         for col in ws.columns:
#             col_letter = col[0].column_letter
#             max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
#             ws.column_dimensions[col_letter].width = max_len + 2

#         for row in ws.iter_rows():
#             for cell in row:
#                 if cell.column_letter == "B":
#                     ws.row_dimensions[cell.row].height = 30

#         out = BytesIO()
#         wb.save(out)
#         out.seek(0)

#         await update.message.reply_document(document=InputFile(out, filename="результат.xlsx"))

#         # Показываем кнопку Start снова
#         keyboard = [[InlineKeyboardButton("Start", callback_data='start_process')]]
#         await update.message.reply_text("Готово. Хотите ещё раз? Нажмите Start", reply_markup=InlineKeyboardMarkup(keyboard))

#     except Exception as e:
#         await update.message.reply_text(f"Ошибка обработки данных. Убедитесь, что формат JSON корректный.\n{str(e)}")

# # Запуск
# def main():
#     app = ApplicationBuilder().token(BOT_TOKEN).build()
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CallbackQueryHandler(button_callback))
#     app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
#     app.add_handler(MessageHandler(filters.TEXT, handle_text))
#     app.run_polling()

# # Запуск
# if __name__ == "__main__":
#     main()





























# import pandas as pd
# from openpyxl import load_workbook
# from openpyxl.styles import Font, Alignment, Border, Side
# from openpyxl.utils import get_column_letter

# # Данные
# data = [
#     {"id": "2.4", "размер": "780x700", "кол-во": 25, "цена": 230000},
#     {"id": "2.1", "размер": "780x700", "кол-во": 2, "цена": 230000},
#     {"id": "2.4", "размер": "1000x900", "кол-во": 5, "цена": 360000},
# ]

# # Преобразуем в DataFrame
# rows = []
# for i, item in enumerate(data, 2):  # Excel строки начнутся с 2 (1 — заголовок)
#     строка = {
#         "№": i - 1,
#         "Наименование": f"Дорожный знак,{item['id']},размер {item['размер']}",
#         "Ед. изм": "шт",
#         "Кол-во": item["кол-во"],
#         "Цена": item["цена"],
#         "Стоимость поставки": "",  # будет формула
#         "НДС ставка": "12%",
#         "НДС сумма": "",           # будет формула
#         "Всего сумма с НДС": ""    # будет формула
#     }
#     rows.append(строка)

# df = pd.DataFrame(rows)

# # Добавляем строку "ИТОГО:" — формулы суммирования
# last_row_excel = len(df) + 2  # +2 из-за заголовка
# df.loc[len(df.index)] = {
#     "№": "ИТОГО:",
#     "Наименование": "",
#     "Ед. изм": "",
#     "Кол-во": f"=SUM(D2:D{last_row_excel - 1})",
#     "Цена": "",
#     "Стоимость поставки": f"=SUM(F2:F{last_row_excel - 1})",
#     "НДС ставка": "",
#     "НДС сумма": f"=SUM(H2:H{last_row_excel - 1})",
#     "Всего сумма с НДС": f"=SUM(I2:I{last_row_excel - 1})"
# }


# # Сохраняем DataFrame
# file_name = "результат_с_формулами.xlsx"
# df.to_excel(file_name, index=False)

# # Загружаем файл для форматирования
# wb = load_workbook(file_name)
# ws = wb.active

# # Формулы для каждой строки (кроме "ИТОГО:")
# for i in range(2, last_row_excel):
#     qty_cell = f"D{i}"
#     price_cell = f"E{i}"
#     cost_cell = f"F{i}"
#     vat_cell = f"H{i}"
#     total_cell = f"I{i}"

#     ws[cost_cell] = f"={qty_cell}*{price_cell}"
#     ws[vat_cell] = f"={cost_cell}*0.12"
#     ws[total_cell] = f"={cost_cell}+{vat_cell}"

# # Стили
# thin_border = Border(
#     left=Side(style='thin'), right=Side(style='thin'),
#     top=Side(style='thin'), bottom=Side(style='thin')
# )
# thick_border = Border(
#     left=Side(style='thick'), right=Side(style='thick'),
#     top=Side(style='thick'), bottom=Side(style='thick')
# )

# for row in ws.iter_rows():
#     for cell in row:
#         row_idx = cell.row
#         cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
#         cell.font = Font(name="Arial", size=10)
#         cell.border = thin_border

#         if row_idx == 1 or row_idx == last_row_excel:
#             cell.font = Font(name="Arial", size=10, bold=True)
#             cell.border = thick_border

# # Автоширина
# for col in ws.columns:
#     max_len = 0
#     col_letter = col[0].column_letter
#     for cell in col:
#         try:
#             val = str(cell.value)
#             if val:
#                 max_len = max(max_len, len(val))
#         except:
#             pass
#     ws.column_dimensions[col_letter].width = max_len + 2

# # Высота строк (для колонки B)
# for row in ws.iter_rows():
#     for cell in row:
#         if cell.column_letter == "B":
#             ws.row_dimensions[cell.row].height = 30

# # Сохраняем результат
# wb.save(file_name)
# print(f"Файл '{file_name}' успешно создан с формулами и форматированием.")







# import cv2
# import pytesseract
# import os
# import numpy as np
# from pathlib import Path
# import re
# from collections import defaultdict

# # === Настройки Tesseract ===
# pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
# # os.environ['TESSDATA_PREFIX'] = r'C:\Program Files\Tesseract-OCR\tessdata_best'

# # === Папка для сохранения ячеек ===
# output_dir = Path("imggen")
# output_dir.mkdir(exist_ok=True)

# # === Загрузка и обработка изображения ===
# img_path = 'qwe.png'  # замените на свой путь к изображению
# img = cv2.imread(img_path)
# if img is None:
#     raise FileNotFoundError(f"❌ Файл '{img_path}' не найден!")

# orig = img.copy()
# gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
# gray = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)

# # === Поиск линий ===
# hsize = int(gray.shape[1] / 15)
# hStruct = cv2.getStructuringElement(cv2.MORPH_RECT, (hsize, 1))
# horizontal = cv2.dilate(cv2.erode(gray, hStruct), hStruct)

# vsize = int(gray.shape[0] / 15)
# vStruct = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vsize))
# vertical = cv2.dilate(cv2.erode(gray, vStruct), vStruct)

# # === Найти контуры ячеек ===
# mask = horizontal + vertical
# contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

# cells = []
# for cnt in contours:
#     x, y, w, h = cv2.boundingRect(cnt)
#     if 30 < w < 1000 and 20 < h < 500:
#         cells.append((x, y, w, h))

# # === Группировка по строкам ===
# cells = sorted(cells, key=lambda b: (b[1], b[0]))
# rows = []
# current_row = []
# last_y = -100
# tolerance = 15

# for cell in cells:
#     x, y, w, h = cell
#     if abs(y - last_y) > tolerance:
#         if current_row:
#             rows.append(sorted(current_row, key=lambda b: b[0]))
#         current_row = [cell]
#         last_y = y
#     else:
#         current_row.append(cell)
# if current_row:
#     rows.append(sorted(current_row, key=lambda b: b[0]))

# # === Сохранение всех ячеек ===
# for i, row in enumerate(rows, start=1):
#     for j, (x, y, w, h) in enumerate(row, start=1):
#         cell_img = orig[y:y+h, x:x+w]
#         filename = output_dir / f"{i}-{j}.png"
#         cv2.imwrite(str(filename), cell_img)

# print("🟢 Все ячейки успешно сохранены в папку imggen/\n")

# # === Распознавание ячеек ===
# table = defaultdict(dict)
# for path in sorted(output_dir.glob("*.png")):
#     match = re.match(r"(\d+)-(\d+)\.png", path.name)
#     if not match:
#         continue
#     row, col = int(match.group(1)), int(match.group(2))

#     img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
#     img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
#     img = cv2.convertScaleAbs(img, alpha=2.0, beta=0)
#     kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
#     img = cv2.filter2D(img, -1, kernel)
#     img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
#                                 cv2.THRESH_BINARY, 11, 2)

#     config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0xXХх123456789XххХ'
#     text = pytesseract.image_to_string(img, lang='rus', config=config )
#     table[row][col] = text.strip().replace('\n', ' ')

# # === Вывод в виде таблицы ===
# print("📋 Распознанная таблица:\n")

# header = ["№", "Знак", "Кол-во", "Размер", "Цена за 1 шт", "Общая сумма"]
# print("| " + " | ".join(header) + " |")
# print("|" + " --- |" * len(header))

# num = 1
# for i in sorted(table):
#     row_cells = [table[i].get(j, '').strip() for j in range(1, 7)]
#     if all(cell == '' for cell in row_cells):
#         continue

#     # Если строка содержит ИТОГО
#     if any("итого" in c.lower() for c in row_cells):
#         total_row = ["", "**ИТОГО:**"] + row_cells[2:3] + ["", "", row_cells[5] if len(row_cells) > 5 else ""]
#         print("| " + " | ".join(total_row) + " |")
#     else:
#         print("|", f"{num}", "|", " | ".join(row_cells), "|")
#         num += 1










# import os
# from flask import Flask, render_template, request, send_file
# from markupsafe import Markup
# from PIL import Image, ImageEnhance, ImageFilter
# import pytesseract
# import pandas as pd
# from io import BytesIO
# import re

# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# app = Flask(__name__)
# UPLOAD_FOLDER = 'uploads'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# @app.route('/')
# def index():
#     return render_template('index.html')

# def preprocess_image(path):
#     img = Image.open(path)
#     img = img.convert('L')
#     img = img.filter(ImageFilter.SHARPEN)
#     img = ImageEnhance.Contrast(img).enhance(2.5)
#     return img

# def clean_text(text):
#     replacements = {
#         '×': 'x', 'х': 'x', 'Х': 'x',
#         'P ': '', 'P': '', 'Р': '', 'р': '',  # часто лишняя буква
#         'O': '0', '|': '1', 'l': '1', 'I': '1',
#         'uwT': 'шт', 'uwit': 'шт', 'штT': 'шт',
#         'шт.': 'шт', 'шт,': 'шт', 'шт ': 'шт',  # убрать пробелы
#         '  ': ' ', '\t': ' ',
#     }
#     for wrong, right in replacements.items():
#         text = text.replace(wrong, right)
#     return text


# @app.route('/upload', methods=['POST'])
# def upload_image():
#     file = request.files['image']
#     if not file:
#         return "Файл не выбран", 400

#     filepath = os.path.join(UPLOAD_FOLDER, file.filename)
#     file.save(filepath)

#     image = preprocess_image(filepath)
#     # config = r'--oem 3 --psm 3'
#     raw_text = pytesseract.image_to_string(image, lang='rus')
#     os.remove(filepath)

#     raw_text = clean_text(raw_text)
#     lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
#     raw_text_display = "<br>".join(lines)

#     rows = []

#     # Шаблоны
#     id_regex = re.compile(r'^(\d+\.\d+(?:\.\d+)?|\w+)$')  # ID: 5.16.1 или слово
#     qty_regex = re.compile(r'(\d+)\s*шт', re.IGNORECASE)
#     size_regex = re.compile(r'\d{2,3}x\d{2,3}')
#     price_regex = re.compile(r'\d{1,3}[.,]\d{3}')
    
#     current_id = None
#     buffer = []

#     for line in lines:
#         if id_regex.match(line):
#             if current_id and buffer:
#                 row = parse_buffer(current_id, buffer)
#                 if row:
#                     rows.append(row)
#             current_id = line
#             buffer = []
#         else:
#             buffer.append(line)

#     if current_id and buffer:
#         row = parse_buffer(current_id, buffer)
#         if row:
#             rows.append(row)

#     if not rows:
#         return f"""
#         <h2>❌ Не удалось распарсить таблицу</h2>
#         <h4>🔍 Вот что tesseract увидел:</h4>
#         <pre style='font-size:16px; background:#f4f4f4; padding:10px'>{raw_text_display}</pre>
#         """, 200

#     # Excel
#     df = pd.DataFrame(rows)
#     df.index += 1
#     df.columns = ["ID", "Количество", "Размер", "Цена за одну", "Общая цена"]

#     output = BytesIO()
#     with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#         df.to_excel(writer, sheet_name='Таблица', index_label="№")
#         workbook = writer.book
#         worksheet = writer.sheets['Таблица']

#         fmt_header = workbook.add_format({'bold': True, 'bg_color': '#F4F4F4', 'border': 1})
#         fmt_cell = workbook.add_format({'border': 1})
#         worksheet.set_column('A:F', 20)

#         headers = ["№"] + list(df.columns)
#         for col_num, val in enumerate(headers):
#             worksheet.write(0, col_num, val, fmt_header)

#         for row_num in range(len(df)):
#             worksheet.write(row_num + 1, 0, row_num + 1, fmt_cell)
#             for col_num in range(len(df.columns)):
#                 worksheet.write(row_num + 1, col_num + 1, df.iloc[row_num, col_num], fmt_cell)

#     output.seek(0)
#     return send_file(
#         output,
#         as_attachment=True,
#         download_name="таблица.xlsx",
#         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )

# # 🔧 Парсинг одной группы строк по одному ID
# def parse_buffer(current_id, buffer):
#     qty = None
#     size = None
#     price = None
#     total = None

#     for item in buffer:
#         if not qty:
#             m = re.search(r'(\d+)\s*шт', item)
#             if m: qty = int(m.group(1))

#         if not size:
#             m = re.search(r'(\d{2,3}x\d{2,3})', item)
#             if m: size = m.group(1)

#         if not price or not total:
#             matches = re.findall(r'\d{1,3}[.,]\d{3}', item)
#             numbers = [int(x.replace('.', '').replace(',', '')) for x in matches]
#             if len(numbers) == 1:
#                 if not price: price = numbers[0]
#             elif len(numbers) >= 2:
#                 price = numbers[0]
#                 total = numbers[1]

#     if current_id and qty and size and price and total:
#         return {
#             "ID": current_id,
#             "Количество": qty,
#             "Размер": size,
#             "Цена за одну": price,
#             "Общая цена": total
#         }
#     return None

# if __name__ == '__main__':
#     app.run(debug=True)
