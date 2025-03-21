import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot_logic import (
    start,
    help_command,
    stop,
    handle_file_message,
    handle_text_message
)
from dotenv import load_dotenv
import os

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен не найден! Проверьте файл .env")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрируем обработчики команд и сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Бот запущен, ожидание сообщений...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
