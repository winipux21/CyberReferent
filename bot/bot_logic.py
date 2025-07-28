import os
import io
import logging
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import ContextTypes
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Импорт всех необходимых модулей из backend (согласно backend/main.py)
from backend.document_parser import extract_text, extract_bibliography_section, split_references_to_list
from backend.reference_validator import validate_references
from backend.gost_ai_formatter import format_gost
from backend.apa_ai_formatter import format_apa_ai
from backend.mla_ai_formatter import format_mla_ai
from backend.text_parser import split_references_from_text
from backend.converter import convert_reference
from backend.web_scraper import extract_bibliographic_data, compose_reference
from backend.tex_bibliography_formatter import format_reference_to_tex
from backend.csv_bibliography_formatter import format_reference_to_csv
from backend.reference_converter import convert_to_format

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные словари для каждого чата
current_processing = {}  # chat_id -> bool
user_settings = {}       # chat_id -> {"mode": ..., "style": ..., "source_format": ..., "target_format": ..., "subformat": ...}
tasks_by_chat = {}       # chat_id -> список asyncio.Task

# Маппинг для нормализации стилей (Cyrillic/Latin -> Latin)
style_mapping = {
    "ГОСТ": "GOST",
    "GOST": "GOST",
    "APA": "APA",
    "MLA": "MLA"
}

# Определение клавиатур
def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("Проверка ссылок"), KeyboardButton("Конвертация ссылок")],
        [KeyboardButton("Сбор данных по URL"), KeyboardButton("Конвертация в CSV")],
        [KeyboardButton("Конвертация в BibTeX"), KeyboardButton("Справка")],
        [KeyboardButton("Стоп")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_style_keyboard():
    keyboard = [[KeyboardButton("ГОСТ"), KeyboardButton("APA"), KeyboardButton("MLA")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_subformat_keyboard(style):
    subformats = {
        "APA": ["Журнальная статья", "Онлайн-журнал", "Сетевое издание", "Книга"],
        "GOST": ["Статья в журнале", "Книга", "Материалы конференций", "Статья в печати", "Онлайн-статья"],
        "MLA": ["Журнальная статья", "Интернет-журнал", "Статья в онлайн-СМИ", "Монография"]
    }
    keyboard = [[KeyboardButton(sub)] for sub in subformats[style]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_processing[chat_id] = True
    user_settings[chat_id] = {"mode": "select_function"}
    tasks_by_chat[chat_id] = []
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    welcome_message = (
        f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
        "Привет! Это бот Cyber-Referent.\n\n"
        "Я могу:\n"
        "- Проверять ссылки по ГОСТ, APA, MLA\n"
        "- Конвертировать ссылки между форматами\n"
        "- Собирать данные с URL\n"
        "- Экспортировать в CSV и BibTeX\n\n"
        "Выберите функцию:"
    )
    await update.message.reply_text(welcome_message, reply_markup=get_main_menu_keyboard())

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    help_message = (
        f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
        "Функции бота:\n"
        "- *Проверка ссылок*: отправьте файл (PDF/DOCX) или текст\n"
        "- *Конвертация ссылок*: укажите исходный и целевой формат, отправьте ссылку\n"
        "- *Сбор данных по URL*: укажите URL и стиль оформления\n"
        "- *Конвертация в CSV*: отправьте ссылку для экспорта в CSV\n"
        "- *Конвертация в BibTeX*: укажите стиль и отправьте ссылку\n\n"
        "Команды:\n"
        "/start – начать работу\n"
        "/stop – остановить текущую операцию\n"
        "/help – справка"
    )
    await update.message.reply_text(help_message, reply_markup=get_main_menu_keyboard())

# Команда /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_processing[chat_id] = False
    if chat_id in tasks_by_chat:
        for task in tasks_by_chat[chat_id]:
            task.cancel()
        tasks_by_chat[chat_id].clear()
    user_settings[chat_id] = {"mode": "select_function"}
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    stop_message = (
        f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
        "Операция остановлена. Выберите новую функцию:"
    )
    await update.message.reply_text(stop_message, reply_markup=get_main_menu_keyboard())

# Обработка проверки ссылок из файла
async def process_check_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    style = user_settings[chat_id]["style"]
    subformat = user_settings[chat_id]["subformat"]
    compiled_citations = []

    try:
        document = update.message.document
        filename = document.file_name.lower()
        if not (filename.endswith('.pdf') or filename.endswith('.docx')):
            await update.message.reply_text("Поддерживаются только файлы PDF и DOCX.", reply_markup=get_main_menu_keyboard())
            return
        logger.info("Получен файл: %s", filename)
        file = await document.get_file()
        file_bytes = await file.download_as_bytearray()
        file_obj = io.BytesIO(file_bytes)
        text = await asyncio.to_thread(extract_text, file_obj, filename)
        bibliography_section = extract_bibliography_section(text)
        if not bibliography_section:
            await update.message.reply_text("Список литературы не найден.", reply_markup=get_main_menu_keyboard())
            return
        references = split_references_to_list(bibliography_section)
        valid_refs, invalid_refs = validate_references(references, style, subformat)
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

        for ref_tuple in valid_refs:
            if not current_processing.get(chat_id, False):
                break
            ref_text = ref_tuple[0]
            message_text = (
                f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
                f"✅ Валидная ссылка:\n```\n{ref_text}\n```"
            )
            await update.message.reply_text(message_text, reply_markup=get_main_menu_keyboard())
            compiled_citations.append(ref_text)

        for ref in invalid_refs:
            if not current_processing.get(chat_id, False):
                break
            analysis = (
                format_gost(ref['original'], subformat) if style == "GOST" else
                format_apa_ai(ref['original'], subformat) if style == "APA" else
                format_mla_ai(ref['original'], subformat)
            )
            message_text = (
                f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
                f"⚠️ Невалидная ссылка:\n"
                f"Оригинал: {ref['original']}\n\n"
                f"Исправление:\n```\n{analysis}\n```"
            )
            await update.message.reply_text(message_text, reply_markup=get_main_menu_keyboard())
            compiled_citations.append(analysis.split('\n')[-1] if style != "GOST" else analysis.split("ГОСТ:")[-1].strip())

        if compiled_citations:
            numbered_citations = "\n\n".join(f"{i+1}. {cit}" for i, cit in enumerate(compiled_citations))
            compiled_message = (
                f"📝 Полный список исправленных ссылок:\n"
                f"```\n{numbered_citations}\n```"
            )
            await update.message.reply_text(compiled_message, reply_markup=get_main_menu_keyboard())

        await update.message.reply_text("🎉 Обработка завершена!", reply_markup=get_main_menu_keyboard())
        user_settings[chat_id]["mode"] = "select_function"

    except Exception as e:
        logger.exception("Ошибка обработки файла:")
        await update.message.reply_text(f"Ошибка: {str(e)}", reply_markup=get_main_menu_keyboard())

# Обработка проверки ссылок из текста
async def process_check_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    style = user_settings[chat_id]["style"]
    subformat = user_settings[chat_id]["subformat"]
    text = update.message.text.strip()
    compiled_citations = []

    try:
        references = split_references_from_text(text)
        valid_refs, invalid_refs = validate_references(references, style, subformat)
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

        for ref_tuple in valid_refs:
            if not current_processing.get(chat_id, False):
                break
            ref_text = ref_tuple[0]
            message_text = (
                f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
                f"✅ Валидная ссылка:\n```\n{ref_text}\n```"
            )
            await update.message.reply_text(message_text, reply_markup=get_main_menu_keyboard())
            compiled_citations.append(ref_text)

        for ref in invalid_refs:
            if not current_processing.get(chat_id, False):
                break
            analysis = (
                format_gost(ref['original'], subformat) if style == "GOST" else
                format_apa_ai(ref['original'], subformat) if style == "APA" else
                format_mla_ai(ref['original'], subformat)
            )
            message_text = (
                f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
                f"⚠️ Невалидная ссылка:\n"
                f"Оригинал: {ref['original']}\n\n"
                f"Исправление:\n```\n{analysis}\n```"
            )
            await update.message.reply_text(message_text, reply_markup=get_main_menu_keyboard())
            compiled_citations.append(analysis.split('\n')[-1] if style != "GOST" else analysis.split("ГОСТ:")[-1].strip())

        if compiled_citations:
            numbered_citations = "\n\n".join(f"{i+1}. {cit}" for i, cit in enumerate(compiled_citations))
            compiled_message = (
                f"📝 Полный список исправленных ссылок:\n"
                f"```\n{numbered_citations}\n```"
            )
            await update.message.reply_text(compiled_message, reply_markup=get_main_menu_keyboard())

        await update.message.reply_text("🎉 Обработка завершена!", reply_markup=get_main_menu_keyboard())
        user_settings[chat_id]["mode"] = "select_function"

    except Exception as e:
        logger.exception("Ошибка обработки текста:")
        await update.message.reply_text(f"Ошибка: {str(e)}", reply_markup=get_main_menu_keyboard())

# Обработка конвертации ссылок
async def process_convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reference = update.message.text.strip()
    source_format = user_settings[chat_id]["source_format"]
    target_format = user_settings[chat_id]["target_format"]
    subformat = user_settings[chat_id]["subformat"]
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    try:
        converted = convert_to_format(reference, target_format, subformat)
        message_text = (
            f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
            f"Оригинал: {reference}\n"
            f"Конвертировано ({target_format} - {subformat}):\n```\n{converted}\n```"
        )
        await update.message.reply_text(message_text, reply_markup=get_main_menu_keyboard())
        user_settings[chat_id]["mode"] = "select_function"
    except Exception as e:
        logger.exception("Ошибка конвертации:")
        await update.message.reply_text(f"Ошибка: {str(e)}", reply_markup=get_main_menu_keyboard())

# Обработка скрапинга URL
async def process_scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    url = update.message.text.strip()
    style = user_settings[chat_id]["style"]
    subformat = user_settings[chat_id]["subformat"]
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    try:
        data = await extract_bibliographic_data(url)
        reference = compose_reference(data, style, subformat)
        message_text = (
            f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
            f"Собранная ссылка ({style} - {subformat}):\n```\n{reference}\n```"
        )
        await update.message.reply_text(message_text, reply_markup=get_main_menu_keyboard())
        user_settings[chat_id]["mode"] = "select_function"
    except Exception as e:
        logger.exception("Ошибка скрапинга:")
        await update.message.reply_text(f"Ошибка: {str(e)}", reply_markup=get_main_menu_keyboard())

# Обработка конвертации в CSV
async def process_to_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reference = update.message.text.strip()
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    try:
        csv_str = format_reference_to_csv(reference)
        message_text = (
            f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
            f"CSV:\n```\n{csv_str}\n```"
        )
        await update.message.reply_text(message_text, reply_markup=get_main_menu_keyboard())
        csv_file = io.BytesIO(csv_str.encode('utf-8'))
        await update.message.reply_document(document=InputFile(csv_file, filename="reference.csv"),
                                            caption="Скачайте CSV-файл")
        user_settings[chat_id]["mode"] = "select_function"
    except Exception as e:
        logger.exception("Ошибка конвертации в CSV:")
        await update.message.reply_text(f"Ошибка: {str(e)}", reply_markup=get_main_menu_keyboard())

# Обработка конвертации в BibTeX
async def process_to_bibtex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reference = update.message.text.strip()
    target_format = user_settings[chat_id]["target_format"]
    subformat = user_settings[chat_id]["subformat"]
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    try:
        bibtex = format_reference_to_tex(reference, target_format, subformat)
        message_text = (
            f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
            f"BibTeX ({target_format} - {subformat}):\n```\n{bibtex}\n```"
        )
        await update.message.reply_text(message_text, reply_markup=get_main_menu_keyboard())
        bib_file = io.BytesIO(bibtex.encode('utf-8'))
        await update.message.reply_document(document=InputFile(bib_file, filename="reference.bib"),
                                            caption="Скачайте BibTeX-файл")
        user_settings[chat_id]["mode"] = "select_function"
    except Exception as e:
        logger.exception("Ошибка конвертации в BibTeX:")
        await update.message.reply_text(f"Ошибка: {str(e)}", reply_markup=get_main_menu_keyboard())

# Обработчик текстовых сообщений
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    mode = user_settings.get(chat_id, {"mode": "select_function"})["mode"]
    text = update.message.text.strip()

    if mode == "select_function":
        if text == "Проверка ссылок":
            user_settings[chat_id]["mode"] = "check_style"
            await update.message.reply_text("Выберите стиль: ГОСТ, APA, MLA", reply_markup=get_style_keyboard())
        elif text == "Конвертация ссылок":
            user_settings[chat_id]["mode"] = "convert_source"
            await update.message.reply_text("Выберите исходный формат: APA, GOST, MLA", reply_markup=get_style_keyboard())
        elif text == "Сбор данных по URL":
            user_settings[chat_id]["mode"] = "scrape_style"
            await update.message.reply_text("Выберите стиль: ГОСТ, APA, MLA", reply_markup=get_style_keyboard())
        elif text == "Конвертация в CSV":
            user_settings[chat_id]["mode"] = "convert_to_csv_input"
            await update.message.reply_text("Отправьте ссылку для конвертации в CSV.")
        elif text == "Конвертация в BibTeX":
            user_settings[chat_id]["mode"] = "bibtex_target"
            await update.message.reply_text("Выберите стиль: ГОСТ, APA, MLA", reply_markup=get_style_keyboard())
        elif text == "Справка":
            await help_command(update, context)
        elif text == "Стоп":
            await stop(update, context)
        else:
            await update.message.reply_text("Выберите функцию:", reply_markup=get_main_menu_keyboard())

    elif mode == "check_style":
        normalized_text = text.upper()
        if normalized_text in style_mapping:
            user_settings[chat_id]["style"] = style_mapping[normalized_text]
            user_settings[chat_id]["mode"] = "check_subformat"
            await update.message.reply_text("Выберите тип записи:", reply_markup=get_subformat_keyboard(user_settings[chat_id]["style"]))
        else:
            await update.message.reply_text("Выберите стиль: ГОСТ, APA, MLA", reply_markup=get_style_keyboard())

    elif mode == "check_subformat":
        style = user_settings[chat_id]["style"]
        if text in [btn[0].text for btn in get_subformat_keyboard(style).keyboard]:
            user_settings[chat_id]["subformat"] = text
            user_settings[chat_id]["mode"] = "check_input"
            await update.message.reply_text("Отправьте файл (PDF/DOCX) или текст для проверки.")
        else:
            await update.message.reply_text("Выберите тип записи:", reply_markup=get_subformat_keyboard(style))

    elif mode == "check_input":
        await update.message.reply_text("Обработка началась...")
        task = asyncio.create_task(process_check_text(update, context))
        tasks_by_chat[chat_id].append(task)

    elif mode == "convert_source":
        normalized_text = text.upper()
        if normalized_text in style_mapping:
            user_settings[chat_id]["source_format"] = style_mapping[normalized_text]
            user_settings[chat_id]["mode"] = "convert_target"
            await update.message.reply_text("Выберите целевой формат: APA, GOST, MLA", reply_markup=get_style_keyboard())
        else:
            await update.message.reply_text("Выберите исходный формат: APA, GOST, MLA", reply_markup=get_style_keyboard())

    elif mode == "convert_target":
        normalized_text = text.upper()
        if normalized_text in style_mapping:
            user_settings[chat_id]["target_format"] = style_mapping[normalized_text]
            user_settings[chat_id]["mode"] = "convert_subformat"
            await update.message.reply_text("Выберите тип записи:", reply_markup=get_subformat_keyboard(user_settings[chat_id]["target_format"]))
        else:
            await update.message.reply_text("Выберите целевой формат: APA, GOST, MLA", reply_markup=get_style_keyboard())

    elif mode == "convert_subformat":
        target_format = user_settings[chat_id]["target_format"]
        if text in [btn[0].text for btn in get_subformat_keyboard(target_format).keyboard]:
            user_settings[chat_id]["subformat"] = text
            user_settings[chat_id]["mode"] = "convert_input"
            await update.message.reply_text("Отправьте ссылку для конвертации.")
        else:
            await update.message.reply_text("Выберите тип записи:", reply_markup=get_subformat_keyboard(target_format))

    elif mode == "convert_input":
        await update.message.reply_text("Обработка началась...")
        task = asyncio.create_task(process_convert(update, context))
        tasks_by_chat[chat_id].append(task)

    elif mode == "scrape_style":
        normalized_text = text.upper()
        if normalized_text in style_mapping:
            user_settings[chat_id]["style"] = style_mapping[normalized_text]
            user_settings[chat_id]["mode"] = "scrape_subformat"
            await update.message.reply_text("Выберите тип записи:", reply_markup=get_subformat_keyboard(user_settings[chat_id]["style"]))
        else:
            await update.message.reply_text("Выберите стиль: ГОСТ, APA, MLA", reply_markup=get_style_keyboard())

    elif mode == "scrape_subformat":
        style = user_settings[chat_id]["style"]
        if text in [btn[0].text for btn in get_subformat_keyboard(style).keyboard]:
            user_settings[chat_id]["subformat"] = text
            user_settings[chat_id]["mode"] = "scrape_input"
            await update.message.reply_text("Отправьте URL для сбора данных.")
        else:
            await update.message.reply_text("Выберите тип записи:", reply_markup=get_subformat_keyboard(style))

    elif mode == "scrape_input":
        await update.message.reply_text("Обработка началась...")
        task = asyncio.create_task(process_scrape(update, context))
        tasks_by_chat[chat_id].append(task)

    elif mode == "convert_to_csv_input":
        await update.message.reply_text("Обработка началась...")
        task = asyncio.create_task(process_to_csv(update, context))
        tasks_by_chat[chat_id].append(task)

    elif mode == "bibtex_target":
        normalized_text = text.upper()
        if normalized_text in style_mapping:
            user_settings[chat_id]["target_format"] = style_mapping[normalized_text]
            user_settings[chat_id]["mode"] = "bibtex_subformat"
            await update.message.reply_text("Выберите тип записи:", reply_markup=get_subformat_keyboard(user_settings[chat_id]["target_format"]))
        else:
            await update.message.reply_text("Выберите стиль: ГОСТ, APA, MLA", reply_markup=get_style_keyboard())

    elif mode == "bibtex_subformat":
        target_format = user_settings[chat_id]["target_format"]
        if text in [btn[0].text for btn in get_subformat_keyboard(target_format).keyboard]:
            user_settings[chat_id]["subformat"] = text
            user_settings[chat_id]["mode"] = "bibtex_input"
            await update.message.reply_text("Отправьте ссылку для конвертации в BibTeX.")
        else:
            await update.message.reply_text("Выберите тип записи:", reply_markup=get_subformat_keyboard(target_format))

    elif mode == "bibtex_input":
        await update.message.reply_text("Обработка началась...")
        task = asyncio.create_task(process_to_bibtex(update, context))
        tasks_by_chat[chat_id].append(task)

# Обработчик файлов
async def handle_file_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    mode = user_settings.get(chat_id, {"mode": "select_function"})["mode"]
    if mode == "check_input":
        await update.message.reply_text("Обработка файла началась...")
        task = asyncio.create_task(process_check_file(update, context))
        tasks_by_chat[chat_id].append(task)
    else:
        await update.message.reply_text("Сначала выберите функцию 'Проверка ссылок'.", reply_markup=get_main_menu_keyboard())