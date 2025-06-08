import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from telegram.constants import ParseMode

# Импортируем наши модули
from . import database
from . import mcp_handler

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
GET_API_KEY = 0


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог сбора API ключа."""
    user = update.effective_user
    logger.info(f"Пользователь {user.username} ({user.id}) запустил команду /start.")

    await update.message.reply_html(
        f"👋 Привет, {user.mention_html()}!\n\n"
        f"Я бот для взаимодействия с OpenProject. "
        f"Чтобы начать, мне нужен ваш персональный API ключ (API token).\n\n"
        f"Нажмите на свой профиль в OpenProject и перейдите в настройки учетной записи."
        f"Перейдите в Маркеры доступа-> + Токен API. \n\n"
        f"Достаточно один раз отправиь мне Ваш ключ и я запомню его навсегда."
    )
    return GET_API_KEY


async def handle_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет полученный API ключ."""
    user = update.effective_user
    api_key = update.message.text.strip()

    if len(api_key) < 20:  # Простая проверка
        await update.message.reply_text(
            "Это не похоже на API ключ. Пожалуйста, проверьте и отправьте снова, или отмените с помощью /cancel.")
        return GET_API_KEY

    database.save_api_key(user.id, api_key)
    logger.info(f"Сохранен API ключ для пользователя {user.id}.")

    await update.message.reply_text(
        "✅ Ваш API ключ успешно сохранен!\n\n"
        "Теперь вы можете отправлять мне запросы. Например: 'покажи все мои проекты'."
    )
    return ConversationHandler.END


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает обычные текстовые сообщения как запросы к MCP агенту."""
    user = update.effective_user
    query = update.message.text
    logger.info(f"Получен запрос от {user.id}: '{query}'")

    api_key = database.get_api_key(user.id)
    if not api_key:
        await update.message.reply_text(
            "Ваш API ключ еще не настроен. Пожалуйста, используйте команду /start, чтобы добавить его."
        )
        return

    await update.message.reply_text("⚙️ Обрабатываю ваш запрос...")
    response_text = await mcp_handler.run_mcp_agent(api_key, query)
    await update.message.reply_text(response_text)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет диалог ввода ключа."""
    logger.info(f"Пользователь {update.effective_user.id} отменил диалог.")
    await update.message.reply_text('Действие отменено.')
    return ConversationHandler.END


def main() -> None:
    """Основная функция для запуска бота."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        print("ОШИБКА: Переменная окружения TELEGRAM_BOT_TOKEN не установлена.")
        return

    database.init_db()
    application = Application.builder().token(telegram_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            GET_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_key)],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Запуск телеграм бота...")
    application.run_polling()

if __name__=="__main__":
    main()