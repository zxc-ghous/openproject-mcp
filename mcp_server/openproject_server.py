from openproject import get_projects, create_task, pretty_projects, \
    get_project_tasks, log_time_on_task, pretty_tasks
import os
import json
from mcp.server.fastmcp import FastMCP



# Инициализируем MCP сервер с именем 'openproject'
mcp = FastMCP("openproject")


@mcp.tool()
async def list_projects() -> str:
    """
    Получает список всех доступных проектов из OpenProject для текущего пользователя.
    """
    USER_API_KEY = os.getenv("OPENPROJECT_API_KEY")
    if not USER_API_KEY:
        return "Ошибка: Ключ API не настроен. Запуск невозможен."
    print(f"DEBUG: API ключ в инструменте (последние 4 символа): {USER_API_KEY[-4:]}")
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
async def new_task(project_id: int, subject: str, description: str = None) -> str:
    """
    Создает новую задачу (work package) в указанном проекте OpenProject.
    Ключ API определяется автоматически из контекста сессии.

    Args:
        project_id: ID проекта, в котором нужно создать задачу.
        subject: Название (заголовок) задачи.
        description: (Опционально) Полное описание задачи.
    """
    USER_API_KEY = os.getenv("OPENPROJECT_API_KEY")
    if not USER_API_KEY:
        return "Ошибка: Ключ API не настроен. Запуск невозможен."

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


@mcp.tool()
async def list_project_tasks(project_id: int) -> str:
    """
    Получает список всех задач для указанного проекта в OpenProject.

    Args:
        project_id (int): ID проекта, для которого нужно получить задачи.

    Returns:
        str: Отформатированная строка со списком задач проекта или сообщение об ошибке/отсутствии задач.
    """
    USER_API_KEY = os.getenv("OPENPROJECT_API_KEY")
    if not USER_API_KEY:
        return "Ошибка: Ключ API не настроен. Запуск невозможен."

    print(f"MCP Tool: Вызов list_project_tasks для проекта ID: {project_id}...")
    tasks = get_project_tasks(api_key=USER_API_KEY, project_id=project_id)

    if tasks is None:
        return f"Не удалось получить список задач для проекта ID: {project_id}. Проверьте лог сервера для деталей."

    if not tasks:
        return f"В проекте ID: {project_id} задачи не найдены."

    # Форматируем ответ в удобный для чтения вид
    formatted_tasks = pretty_tasks(tasks)

    return f"Найдены следующие задачи в проекте ID {project_id}:\n" + formatted_tasks


@mcp.tool()
async def log_time(task_id: int, hours: float, comment: str = None) -> str:
    """
    Регистрирует затраченное время на выполнение задачи в OpenProject.

    Args:
        task_id (int): ID задачи, на которую регистрируется время.
        hours (float): Количество затраченных часов (может быть дробным, например, 2.5 для 2 часов 30 минут).
        comment (str, optional): Комментарий к записи времени. По умолчанию None.

    Returns:
        str: Сообщение о результате регистрации времени.
    """
    USER_API_KEY = os.getenv("OPENPROJECT_API_KEY")
    if not USER_API_KEY:
        return "Ошибка: Ключ API не настроен. Запуск невозможен."

    print(f"MCP Tool: Вызов log_time для задачи ID: {task_id}, время: {hours} ч, комментарий: '{comment}'...")

    # Проверка на отрицательное время
    if hours < 0:
        return "Ошибка: Нельзя зарегистрировать отрицательное время."

    result = log_time_on_task(api_key=USER_API_KEY, task_id=task_id, hours=hours, comment=comment)

    if result:
        return f"Время успешно зарегистрировано: {hours} ч на задачу ID: {task_id}."
    else:
        return f"Не удалось зарегистрировать время ({hours} ч) на задачу ID: {task_id}. Проверьте лог сервера для деталей."


if __name__ == "__main__":
    print("Инициализация MCP сервера для OpenProject...")
    # Здесь можно оставить проверку, но она уже не будет влиять на работу инструментов
    # так как каждый инструмент будет считывать переменную окружения самостоятельно.
    api_key_from_env = os.getenv("OPENPROJECT_API_KEY")

    if not api_key_from_env:
        print("Внимание: Переменная окружения OPENPROJECT_API_KEY не установлена на этапе запуска сервера. Это нормально, если ключ передается через параметры запуска MCP клиента.")
    else:
        print(f"Контекст пользователя успешно загружен. API ключ '...{api_key_from_env[-4:]}' установлен.")

    print("Запуск MCP сервера...")
    mcp.run(transport='stdio')
