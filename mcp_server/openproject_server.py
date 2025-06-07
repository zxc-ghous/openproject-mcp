from openproject import get_projects, create_task, pretty_projects
import os
import json
from mcp.server.fastmcp import FastMCP

# --- Контекст Пользователя ---
# Эта переменная будет хранить API ключ, полученный из окружения.
# В реальном приложении здесь мог бы быть целый класс для управления сессией.
USER_API_KEY = None

# Инициализируем MCP сервер с именем 'openproject'
mcp = FastMCP("openproject")


@mcp.tool()
async def list_projects() -> str:
    """
    Получает список всех доступных проектов из OpenProject для текущего пользователя.
    Ключ API определяется автоматически из контекста сессии.
    """
    if not USER_API_KEY:
        return "Ошибка: Ключ API не настроен на сервере. Запуск невозможен."

    print("MCP Tool: Вызов list_projects...")
    projects = get_projects(api_key=USER_API_KEY)

    if projects is None:
        return "Не удалось получить список проектов. Проверьте лог сервера для деталей."

    if not projects:
        return "Проекты не найдены."

    # Форматируем ответ в удобный для чтения вид
    formatted_projects = pretty_projects(projects)

    return "Найдены следующие проекты:\n" + "\n".join(formatted_projects)


@mcp.tool()
async def new_task(project_id: int, subject: str, description: str | None = None) -> str:
    """
    Создает новую задачу (work package) в указанном проекте OpenProject.
    Ключ API определяется автоматически из контекста сессии.

    Args:
        project_id: ID проекта, в котором нужно создать задачу.
        subject: Название (заголовок) задачи.
        description: (Опционально) Полное описание задачи.
    """
    if not USER_API_KEY:
        return "Ошибка: Ключ API не настроен на сервере. Запуск невозможен."

    print(f"MCP Tool: Вызов new_task для проекта ID {project_id} с заголовком '{subject}'")
    task_result = create_task(
        api_key=USER_API_KEY,
        project_id=project_id,
        subject=subject,
        description=description
    )

    if task_result and 'id' in task_result:
        task_id = task_result.get('id')
        task_subject = task_result.get('subject')
        return f"Задача '{task_subject}' успешно создана с ID: {task_id}."
    else:
        return f"Не удалось создать задачу '{subject}' в проекте {project_id}. Проверьте лог сервера."


if __name__ == "__main__":
    print("Инициализация MCP сервера для OpenProject...")

    # --- ЗАГРУЗКА КОНТЕКСТА ---
    # Сервер считывает ключ API из переменной окружения.
    # Ваш Telegram-бот должен будет установить эту переменную перед запуском этого скрипта.
    api_key_from_env = os.getenv("OPENPROJECT_API_KEY")

    if not api_key_from_env:
        print("КРИТИЧЕСКАЯ ОШИБКА: Переменная окружения OPENPROJECT_API_KEY не установлена.")
        print("Сервер не может работать без API ключа пользователя.")
        exit(1)  # Завершаем работу, если ключ не предоставлен

    USER_API_KEY = api_key_from_env
    print(f"Контекст пользователя успешно загружен. API ключ '...{USER_API_KEY[-4:]}' установлен.")

    # Запускаем сервер для работы через стандартные потоки ввода-вывода (stdio)
    print("Запуск MCP сервера...")
    mcp.run(transport='stdio')
