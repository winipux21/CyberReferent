import os
import io
import logging
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from dotenv import load_dotenv

# Загружаем переменные из .env (если нужно, можно оставить в main)
load_dotenv()

# Импорт модулей из backend
from backend.document_parser import extract_text, extract_bibliography_section, split_references_to_list
from backend.reference_validator import load_vak_list, validate_references
from backend.gost_formatter import format_references
from backend.gost_ai_formatter import format_gost
from backend.apa_formatter import format_apa
from backend.apa_ai_formatter import format_apa_ai
from backend.mla_formatter import format_mla
from backend.mla_ai_formatter import format_mla_ai
from backend.recommendation_engine import ReferenceRecommender
from backend.text_parser import split_references_from_text

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные словари для каждого чата
current_processing = {}  # chat_id -> bool
user_style = {}          # chat_id -> выбранный формат ("ГОСТ", "APA", "MLA")
tasks_by_chat = {}       # chat_id -> список asyncio.Task

# Загрузка данных ВАК и инициализация рекомендательного модуля
vak_df = load_vak_list('data/VAK_journals.csv')
recommender = ReferenceRecommender(vak_df)

def get_main_keyboard():
    keyboard = [[KeyboardButton("Старт"), KeyboardButton("Стоп")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_style_keyboard():
    keyboard = [[KeyboardButton("ГОСТ"), KeyboardButton("APA"), KeyboardButton("MLA")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def extract_gost_citation(text: str) -> str:
    """
    Извлекает из форматированного текста только ту часть, которая должна идти в качестве ГОСТ.
    Если в тексте присутствует раздел "Примечание:", то он отсекается.
    Если метка "ГОСТ:" отсутствует, возвращается весь текст.
    """
    if "ГОСТ:" in text:
        citation = text.split("ГОСТ:")[-1].strip()
        if "Примечание:" in citation:
            citation = citation.split("Примечание:")[0].strip()
        return citation
    return text.strip()

def extract_formatted_citation(formatted_text: str, style: str) -> str:
    """
    Универсальная функция для извлечения готовой цитаты по заданному стилю (APA или MLA).
    Ищет в тексте маркер вида "APA:" или "MLA:", возвращает часть после него.
    Отсекает блок "Примечание:", если он присутствует.
    """
    marker = f"{style}:"
    if marker in formatted_text:
        citation = formatted_text.split(marker, 1)[-1].strip()
        if "Примечание:" in citation:
            citation = citation.split("Примечание:")[0].strip()
        return citation
    return formatted_text.strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    welcome_message = (
        f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
        "Привет! Это бот 👩🏻‍💻Cyber-Referent.\n\n"
        "Я проверяю библиографические ссылки по стандартам ГОСТ, APA и MLA.\n\n"
        "Пожалуйста, выберите один из форматов ниже:"
    )
    chat_id = update.effective_chat.id
    current_processing[chat_id] = True
    tasks_by_chat[chat_id] = []
    await update.message.reply_text(welcome_message, reply_markup=get_style_keyboard())

async def set_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chosen = update.message.text.strip().upper()
    if chosen not in ["ГОСТ", "APA", "MLA"]:
        await update.message.reply_text(
            "Пожалуйста, выберите один из предложенных форматов: ГОСТ, APA или MLA.",
            reply_markup=get_style_keyboard()
        )
        return
    user_style[chat_id] = chosen
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning("Не удалось удалить сообщение: %s", e)
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    message = (
        f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
        f"Вы выбрали формат: {chosen}.\n\n"
        "Теперь вы можете отправлять свои ссылки или файл для проверки."
    )
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    help_message = (
        f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
        "Для проверки библиографии отправьте файл PDF/DOCX или текст библиографического списка.\n\n"
        "Сначала выберите формат оформления (ГОСТ, APA, MLA) с помощью соответствующих кнопок.\n\n"
        "Команды:\n"
        "/start – начать работу\n"
        "/stop – остановить текущую операцию\n"
        "/help – справка"
    )
    await update.message.reply_text(help_message, reply_markup=get_main_keyboard())

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    current_processing[chat_id] = False
    if chat_id in tasks_by_chat:
        for task in tasks_by_chat[chat_id]:
            task.cancel()
        tasks_by_chat[chat_id].clear()
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    stop_message = f"👩🏻‍💻Cyber-Referent, [{current_time}]\nОперация остановлена. Жду новых данных."
    await update.message.reply_text(stop_message, reply_markup=get_main_keyboard())

async def process_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    compiled_citations = []  # Список для сохранения исправленных ссылок
    try:
        document = update.message.document
        if document:
            filename = document.file_name.lower()
            if not (filename.endswith('.pdf') or filename.endswith('.docx')):
                await update.message.reply_text("Поддерживаются только файлы PDF и DOCX.", reply_markup=get_main_keyboard())
                return
            logger.info("Получен файл: %s", filename)
            file = await document.get_file()
            file_bytes = await file.download_as_bytearray()
            file_obj = io.BytesIO(file_bytes)
            text = await asyncio.to_thread(extract_text, file_obj, filename)
            bibliography_section = await asyncio.to_thread(extract_bibliography_section, text)
            if not bibliography_section:
                await update.message.reply_text("Секция 'Список литературы' не найдена в документе.", reply_markup=get_main_keyboard())
                return
            references = await asyncio.to_thread(split_references_to_list, bibliography_section)
            valid_refs, invalid_refs = await asyncio.to_thread(validate_references, references, vak_df)
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            style_chosen = user_style.get(chat_id, "ГОСТ")

            # Обработка валидных ссылок
            for ref_tuple in valid_refs:
                if not current_processing.get(chat_id, False):
                    logger.info("Обработка отменена пользователем.")
                    break
                ref = ref_tuple[0]
                logger.info("Обрабатываю валидную ссылку: %s", ref)
                if style_chosen == "ГОСТ":
                    formatted_refs = await asyncio.to_thread(format_references, [ref_tuple])
                    formatted_ref = formatted_refs[0]
                    citation = extract_gost_citation(formatted_ref)
                elif style_chosen == "APA":
                    formatted_ref = await asyncio.to_thread(format_apa, ref)
                    citation = extract_formatted_citation(formatted_ref, "APA")
                elif style_chosen == "MLA":
                    formatted_ref = await asyncio.to_thread(format_mla, ref)
                    citation = extract_formatted_citation(formatted_ref, "MLA")

                message_text = (
                    f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
                    f"✅ *Валидная ссылка:*\n\n"
                    f"{style_chosen}:\n```\n{citation}\n```"
                )
                await update.message.reply_text(message_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
                compiled_citations.append(citation)

            # Обработка невалидных ссылок
            for ref in invalid_refs:
                if not current_processing.get(chat_id, False):
                    logger.info("Обработка отменена пользователем.")
                    break
                logger.info("Обрабатываю невалидную ссылку: %s", ref)
                if style_chosen == "ГОСТ":
                    analysis = await asyncio.to_thread(format_gost, ref)
                    citation = extract_gost_citation(analysis)
                elif style_chosen == "APA":
                    analysis = await asyncio.to_thread(format_apa_ai, ref)
                    citation = extract_formatted_citation(analysis, "APA")
                elif style_chosen == "MLA":
                    analysis = await asyncio.to_thread(format_mla_ai, ref)
                    citation = extract_formatted_citation(analysis, "MLA")

                recommendations = await asyncio.to_thread(recommender.recommend_similar, ref, 1)
                rec_journal = recommendations[0][0] if recommendations else "Нет рекомендации"
                rec_issn = recommendations[0][1] if recommendations else ""

                message_text = (
                    f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
                    f"⚠️ *Невалидная ссылка:*\n\n"
                    f"*Исходная:* {ref}\n\n"
                    f"*Ошибки и корректировки:*\n{analysis}\n\n"
                    f"*Рекомендуемый журнал:* {rec_journal} (ISSN: {rec_issn})\n\n"
                    f"{style_chosen}:\n```\n{citation}\n```"
                )
                await update.message.reply_text(message_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
                compiled_citations.append(citation)

            # После обработки всех ссылок отправляем сформированный список для копирования с нумерацией
            if compiled_citations:
                numbered_citations = "\n\n".join(f"{i+1}. {citation}" for i, citation in enumerate(compiled_citations))
                compiled_message = (
                    f"📝 *Полный список исправленных ссылок:*\n"
                    f"```\n{numbered_citations}\n```"
                )
                await update.message.reply_text(compiled_message, parse_mode="Markdown", reply_markup=get_main_keyboard())

            final_message = (
                "🎉 *Обработка завершена!*\n"
                "Вся литература успешно обработана. Спасибо, что воспользовались Cyber-Referent. "
                "Надеюсь, наша помощь была полезной и вдохновляющей для дальнейших исследований!"
            )
            await update.message.reply_text(final_message, parse_mode="Markdown", reply_markup=get_main_keyboard())

    except asyncio.CancelledError:
        logger.info("Обработка файла отменена.")
    except Exception as e:
        logger.exception("Ошибка при обработке файла:")
        await update.message.reply_text(f"Ошибка при обработке файла: {str(e)}", reply_markup=get_main_keyboard())

async def process_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    compiled_citations = []  # Список для сохранения исправленных ссылок
    try:
        text = update.message.text.strip()
        references = await asyncio.to_thread(split_references_from_text, text)
        valid_refs, invalid_refs = await asyncio.to_thread(validate_references, references, vak_df)
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        style_chosen = user_style.get(chat_id, "ГОСТ")

        # Обработка валидных ссылок
        for ref_tuple in valid_refs:
            if not current_processing.get(chat_id, False):
                logger.info("Обработка отменена пользователем.")
                break
            ref = ref_tuple[0]
            logger.info("Обрабатываю валидную ссылку: %s", ref)
            if style_chosen == "ГОСТ":
                formatted_refs = await asyncio.to_thread(format_references, [ref_tuple])
                formatted_ref = formatted_refs[0]
                citation = extract_gost_citation(formatted_ref)
            elif style_chosen == "APA":
                formatted_ref = await asyncio.to_thread(format_apa, ref)
                citation = extract_formatted_citation(formatted_ref, "APA")
            elif style_chosen == "MLA":
                formatted_ref = await asyncio.to_thread(format_mla, ref)
                citation = extract_formatted_citation(formatted_ref, "MLA")

            message_text = (
                f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
                f"✅ *Валидная ссылка:*\n\n"
                f"{style_chosen}:\n```\n{citation}\n```"
            )
            await update.message.reply_text(message_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
            compiled_citations.append(citation)

        # Обработка невалидных ссылок
        for ref in invalid_refs:
            if not current_processing.get(chat_id, False):
                logger.info("Обработка отменена пользователем.")
                break
            logger.info("Обрабатываю невалидную ссылку: %s", ref)
            if style_chosen == "ГОСТ":
                analysis = await asyncio.to_thread(format_gost, ref)
                citation = extract_gost_citation(analysis)
            elif style_chosen == "APA":
                analysis = await asyncio.to_thread(format_apa_ai, ref)
                citation = extract_formatted_citation(analysis, "APA")
            elif style_chosen == "MLA":
                analysis = await asyncio.to_thread(format_mla_ai, ref)
                citation = extract_formatted_citation(analysis, "MLA")

            recommendations = await asyncio.to_thread(recommender.recommend_similar, ref, 1)
            rec_journal = recommendations[0][0] if recommendations else "Нет рекомендации"
            rec_issn = recommendations[0][1] if recommendations else ""

            message_text = (
                f"👩🏻‍💻Cyber-Referent, [{current_time}]\n"
                f"⚠️ *Невалидная ссылка:*\n\n"
                f"*Исходная:* {ref}\n\n"
                f"*Ошибки и корректировки:*\n{analysis}\n\n"
                f"*Рекомендуемый журнал:* {rec_journal} (ISSN: {rec_issn})\n\n"
                f"{style_chosen}:\n```\n{citation}\n```"
            )
            await update.message.reply_text(message_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
            compiled_citations.append(citation)

        # После обработки всех ссылок отправляем сформированный список для копирования с нумерацией
        if compiled_citations:
            numbered_citations = "\n\n".join(f"{i+1}. {citation}" for i, citation in enumerate(compiled_citations))
            compiled_message = (
                f"📝 *Полный список исправленных ссылок:*\n"
                f"```\n{numbered_citations}\n```"
            )
            await update.message.reply_text(compiled_message, parse_mode="Markdown", reply_markup=get_main_keyboard())

        final_message = (
            "🎉 *Обработка завершена!*\n"
            "Вся литература успешно обработана. Спасибо, что воспользовались Cyber-Referent. "
            "Желаем вам успехов в дальнейших научных исследованиях и оформлении библиографических списков!"
        )
        await update.message.reply_text(final_message, parse_mode="Markdown", reply_markup=get_main_keyboard())

    except asyncio.CancelledError:
        logger.info("Обработка текста отменена.")
    except Exception as e:
        logger.exception("Ошибка при обработке текста:")
        await update.message.reply_text(f"Ошибка при обработке текста: {str(e)}", reply_markup=get_main_keyboard())

async def handle_file_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Файл получен. Обработка началась...", reply_markup=get_main_keyboard())
    task = asyncio.create_task(process_file(update, context))
    tasks_by_chat.setdefault(update.effective_chat.id, []).append(task)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "старт":
        await start(update, context)
    elif text.lower() == "стоп":
        await stop(update, context)
    elif text.upper() in ["ГОСТ", "APA", "MLA"]:
        await set_style(update, context)
    else:
        await update.message.reply_text("Обработка текста началась...", reply_markup=get_main_keyboard())
        task = asyncio.create_task(process_text(update, context))
        tasks_by_chat.setdefault(update.effective_chat.id, []).append(task)
