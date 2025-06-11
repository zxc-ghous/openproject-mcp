import os
import logging

import telegram.error
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from telegram.constants import ParseMode

# Импортируем наши модули
from . import database
from . import mcp_handler
from dotenv import load_dotenv
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
GET_API_KEY = 0


# TODO: разделить логирование ТГ бота и MCP клиента
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет сообщение о возможностях бота."""
    help_text = (
        "Я бот для взаимодействия с OpenProject. Вот что я умею:\n\n"
        "➡️ /start - Начать работу с ботом и настроить ваш API ключ.\n"
        "➡️ /help - Показать это справочное сообщение.\n"
        "➡️ /cancel - Отменить текущую операцию (например, ввод API ключа).\n\n"
        "После настройки API ключа вы можете давать мне следующие команды на естественном языке:\n"
        "🔹 <b>'Покажи все проекты'</b> - Получить список всех доступных проектов.\n"
        "🔹 <b>'Создай задачу [название_задачи] в проекте [ID_проекта] [опционально: с описанием [описание]]'</b> - Создать новую задачу.\n"
        "   <i>Пример: 'Создай задачу Новая фича в проекте 123 с описанием Реализовать авторизацию'</i> \n"
        "🔹 <b>'Покажи задачи в проекте [ID_проекта]'</b> - Получить список всех задач в указанном проекте.\n"
        "   <i>Пример: 'Покажи задачи в проекте 456'</i> \n"
        "🔹 <b>'Зарегистрируй [N] часов на задачу [ID_задачи] [опционально: с комментарием [комментарий]]'</b> - Зарегистрировать затраченное время на задачу.\n"
        "   <i>Пример: 'Зарегистрируй 2.5 часа на задачу 789 с комментарием Проверка кода'</i> \n\n"
        "Пожалуйста, используйте ID проекта/задачи при запросах, если я не могу определить их по контексту."
    )
    await update.message.reply_html(help_text) # Используем reply_html вместо reply_text


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог сбора API ключа."""
    user = update.effective_user
    logger.info(f"Пользователь {user.username} ({user.id}) запустил команду /start.")
    await help_command(update, context)
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

    if len(api_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in api_key):
        database.save_api_key(user.id, api_key)
        logger.info(f"Сохранен API ключ для пользователя {user.id}.")

        await update.message.reply_text(
            "✅ Ваш API ключ успешно сохранен!\n\n"
            "Теперь вы можете отправлять мне запросы. Например: 'покажи все мои проекты'."
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Это не похоже на корректный API ключ OpenProject. "
        )
        return GET_API_KEY


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает обычные текстовые сообщения как запросы к MCP агенту."""
    user = update.effective_user
    thread_id = str(user.id)
    query = update.message.text
    logger.info(f"Получен запрос от {user.id}: '{query}'")

    api_key = database.get_api_key(user.id)
    if not api_key:
        await update.message.reply_text(
            "Ваш API ключ еще не настроен. Пожалуйста, используйте команду /start, чтобы добавить его."
        )
        return

    processing_message = await update.message.reply_markdown_v2("⚙️ Обрабатываю ваш запрос")
    response_text = await mcp_handler.run_mcp_agent(api_key, query, thread_id)
    try:
        await processing_message.edit_text(response_text, parse_mode=ParseMode.MARKDOWN_V2)
    except telegram.error.BadRequest as e:
        logger.error(f"Ошибка форматирования {e}")
        await processing_message.edit_text(response_text)


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
    application.add_handler(CommandHandler("help", help_command))  # <-- Добавлена эта строка
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Запуск телеграм бота...")
    application.run_polling()


if __name__ == "__main__":
    main()
