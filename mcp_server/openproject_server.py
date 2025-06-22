from openproject import *
import os
import json
from mcp.server.fastmcp import FastMCP
from config import setup_logger
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
log_path = Path(r"logs")
logger = setup_logger('server', log_path)

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
    OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")
    if not OPENPROJECT_URL:
        logger.error("Переменная окружения OPENPROJECT_URL не установлена. Запросы к OpenProject могут не работать.")
    logger.info("MCP Tool: Вызов list_projects...")
    projects = await get_projects(api_key=USER_API_KEY, OPENPROJECT_URL=OPENPROJECT_URL)

    if projects is None:
        logger.error(f"Не удалось получить список проектов", exc_info=True)
        return "Не удалось получить список проектов. Проверьте лог сервера для деталей."

    if not projects:
        return "Проекты не найдены."

    # Форматируем ответ в удобный для чтения вид
    formatted_projects = pretty_projects(projects)

    return "Найдены следующие проекты:\n" + "\n".join(formatted_projects)


# @mcp.tool()
# async def new_task(project_id: int, subject: str, description: str = None) -> str:
#     """
#     Создает новую задачу (work package) в указанном проекте OpenProject.
#     Args:
#         project_id: ID проекта, в котором нужно создать задачу.
#         subject: Название (заголовок) задачи.
#         description: (Опционально) Полное описание задачи.
#     """
#     USER_API_KEY = os.getenv("OPENPROJECT_API_KEY")
#     if not USER_API_KEY:
#         return "Ошибка: Ключ API не настроен. Запуск невозможен."
#     OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")
#     if not OPENPROJECT_URL:
#         logger.error("Переменная окружения OPENPROJECT_URL не установлена. Запросы к OpenProject могут не работать.")
#     logger.info(f"MCP Tool: Вызов new_task для проекта ID {project_id} с заголовком '{subject}'")
#     task_result = await create_task(
#         api_key=USER_API_KEY,
#         OPENPROJECT_URL=OPENPROJECT_URL,
#         project_id=project_id,
#         subject=subject,
#         description=description
#     )
#
#     if task_result and 'id' in task_result:
#         task_id = task_result.get('id')
#         task_subject = task_result.get('subject')
#         return f"Задача '{task_subject}' успешно создана с ID: {task_id}."
#     else:
#         logger.error(f"Не удалось создать задачу '{subject}' в проекте {project_id}", exc_info=True)
#         return f"Не удалось создать задачу '{subject}' в проекте {project_id}. Проверьте лог сервера."


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
    OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")
    if not OPENPROJECT_URL:
        logger.error("Переменная окружения OPENPROJECT_URL не установлена. Запросы к OpenProject могут не работать.")
    logger.info(f"MCP Tool: Вызов list_project_tasks для проекта ID: {project_id}...")
    tasks = await get_project_tasks(api_key=USER_API_KEY, OPENPROJECT_URL=OPENPROJECT_URL, project_id=project_id)

    if tasks is None:
        logger.error(f"Не удалось получить список задач для проекта ID: {project_id}.", exc_info=True)
        return f"Не удалось получить список задач для проекта ID: {project_id}. Проверьте лог сервера для деталей."

    if not tasks:
        return f"В проекте ID: {project_id} задачи не найдены."

    # Форматируем ответ в удобный для чтения вид
    formatted_tasks = pretty_tasks(tasks)

    return f"Найдены следующие задачи в проекте ID {project_id}:\n" + formatted_tasks


@mcp.tool()
async def list_task_attachments(work_package_id: int) -> str:
    """
    Получает список всех вложений (которые пользователь иногда называет "документами")
    для указанной задачи (Work Package) в OpenProject.

    Args:
        work_package_id (int): ID задачи (Work Package), для которой нужно получить вложения.

    Returns:
        str: Отформатированная строка со списком вложений или сообщение об ошибке/отсутствии вложений.
    """
    USER_API_KEY = os.getenv("OPENPROJECT_API_KEY")
    if not USER_API_KEY:
        logger.error("Ошибка: Ключ API OpenProject не настроен (OPENPROJECT_API_KEY). Запуск tool невозможен.")
        return "Ошибка: Ключ API OpenProject не настроен. Запуск tool невозможен."

    OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")
    if not OPENPROJECT_URL:
        logger.error("Переменная окружения OPENPROJECT_URL не установлена. Запросы к OpenProject могут не работать.")
        return "Ошибка: URL OpenProject не настроен. Запросы к OpenProject могут не работать."

    logger.info(f"MCP Tool: Вызов list_task_attachments для задачи ID: {work_package_id}...")

    attachments = await get_work_package_attachments(
        api_key=USER_API_KEY,
        OPENPROJECT_URL=OPENPROJECT_URL,
        work_package_id=work_package_id
    )

    if attachments is None:
        logger.error(f"Не удалось получить список вложений для задачи ID: {work_package_id}.", exc_info=True)
        return f"Не удалось получить список вложений для задачи ID: {work_package_id}. Проверьте лог сервера для деталей."

    if not attachments:
        return f"Для задачи ID: {work_package_id} вложения не найдены."

    # Форматируем ответ в удобный для чтения вид с помощью вашей функции
    formatted_attachments_string = format_attachments(attachments)

    return f"Найдены следующие вложения для задачи ID {work_package_id}:\n" + formatted_attachments_string

@mcp.tool()
async def update_task_dates(
        work_package_id: int,
        start_date: str = None,
        end_date: str = None
) -> str:
    """
    Обновляет или удаляет начальную и/или конечную дату задачи (Work Package) в OpenProject.
    Функция пытается автоматически распознать даты из разных форматов (например, DD.MM.YYYY, DD-MM-YYYY).
    Рекомендуемый формат: 'YYYY-MM-DD'.
    Для удаления даты используйте специальное строковое значение "DELETE".

    Args:
        work_package_id (int): ID задачи, которую нужно изменить.
        start_date (Optional[str]): Новая начальная дата (например, '21.06.2025') или "DELETE" для удаления.
        end_date (Optional[str]): Новая конечная дата (например, '30-06-2025') или "DELETE" для удаления.

    Returns:
        str: Отформатированное сообщение о результате операции (успех или ошибка).
    """
    # --- ВОССТАНОВЛЕНА ВАША ПРОВЕРКА КЛЮЧЕЙ И URL ---
    USER_API_KEY = os.getenv("OPENPROJECT_API_KEY")
    if not USER_API_KEY:
        logger.error("Ошибка: Ключ API OpenProject не настроен (OPENPROJECT_API_KEY).")
        return "Ошибка: Ключ API не настроен. Запуск невозможен."

    OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")
    if not OPENPROJECT_URL:
        logger.error("Ошибка: URL OpenProject не настроен (OPENPROJECT_URL).")
        return "Ошибка: URL OpenProject не настроен. Запуск невозможен."

    logger.info(f"MCP Tool: Вызов update_task_dates для задачи ID {work_package_id} "
                f"с start_date='{start_date}' и end_date='{end_date}'")

    # --- ДОБАВЛЕН БЛОК РАСПОЗНАВАНИЯ И ВАЛИДАЦИИ ДАТ ---
    parsed_start_date = parse_and_format_date(start_date)
    if start_date and parsed_start_date is None:
        return f"Ошибка: не удалось распознать начальную дату '{start_date}'. Пожалуйста, используйте формат ГГГГ-ММ-ДД или команду 'DELETE'."

    parsed_end_date = parse_and_format_date(end_date)
    if end_date and parsed_end_date is None:
        return f"Ошибка: не удалось распознать конечную дату '{end_date}'. Пожалуйста, используйте формат ГГГГ-ММ-ДД или команду 'DELETE'."

    # Вызываем вашу низкоуровневую функцию с отформатированными датами
    task_result = await update_work_package_dates(
        api_key=USER_API_KEY,
        OPENPROJECT_URL=OPENPROJECT_URL,
        work_package_id=work_package_id,
        start_date=parsed_start_date,
        end_date=parsed_end_date
    )

    if task_result:
        logger.info(f"Успешно обновлена задача ID: {work_package_id}.")

        # --- ВОССТАНОВЛЕНО ВАШЕ ОРИГИНАЛЬНОЕ ФОРМАТИРОВАНИЕ ОТВЕТА ---
        messages = [f"Задача ID {work_package_id} успешно обновлена."]

        # Проверяем оригинальный ввод, чтобы сформировать правильное сообщение
        if start_date is not None:
            if start_date.upper() == "DELETE":
                messages.append("Начальная дата удалена.")
            else:
                messages.append(f"Новая начальная дата: {task_result.get('startDate')}.")

        if end_date is not None:
            if end_date.upper() == "DELETE":
                messages.append("Конечная дата удалена.")
            else:
                messages.append(f"Новая конечная дата: {task_result.get('dueDate')}.")

        # Восстановлена проверка на случай, если даты не были переданы
        if not (start_date is not None or end_date is not None):
            return "Не указаны даты для изменения или удаления. Никаких действий не выполнено."

        return " ".join(messages)
    else:
        logger.error(f"Не удалось обновить даты для задачи ID: {work_package_id}.")
        return f"Не удалось обновить даты для задачи ID: {work_package_id}. Проверьте лог сервера для деталей."


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
    OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")
    if not OPENPROJECT_URL:
        logger.error("Переменная окружения OPENPROJECT_URL не установлена. Запросы к OpenProject могут не работать.")
    logger.info(f"MCP Tool: Вызов log_time для задачи ID: {task_id}, время: {hours} ч, комментарий: '{comment}'...")

    # Проверка на отрицательное время
    if hours < 0:
        return "Ошибка: Нельзя зарегистрировать отрицательное время."

    result = await log_time_on_task(api_key=USER_API_KEY, OPENPROJECT_URL=OPENPROJECT_URL, task_id=task_id, hours=hours,
                              comment=comment)

    if result:
        return f"Время успешно зарегистрировано: {hours} ч на задачу ID: {task_id}."
    else:
        logger.error(f"Не удалось зарегистрировать время на задачу ID: {task_id}", exc_info=True)
        return f"Не удалось зарегистрировать время ({hours} ч) на задачу ID: {task_id}. Проверьте лог сервера для деталей."


@mcp.tool()
async def get_time_report(start_date: str, end_date: str, project_id: int = None) -> str:
    """
    Получает отчет по затраченному времени в OpenProject за указанный промежуток.
    Отчет может быть отфильтрован по конкретному проекту.

    Args:
        start_date (str): Начальная дата отчета в формате 'YYYY-MM-DD'.
        end_date (str): Конечная дата отчета в формате 'YYYY-MM-DD'.
        project_id (int, optional): ID проекта для фильтрации отчета. Если не указан,
                                     возвращается общий отчет по всем проектам.
                                     По умолчанию None.

    Returns:
        str: Отформатированное сообщение с отчетом о затраченном времени.
    """
    USER_API_KEY = os.getenv("OPENPROJECT_API_KEY")
    if not USER_API_KEY:
        return "Ошибка: Ключ API OpenProject не настроен. Запуск инструмента невозможен."
    OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")
    if not OPENPROJECT_URL:
        logger.error("Переменная окружения OPENPROJECT_URL не установлена. Запросы к OpenProject могут не работать.")
    logger.info(
        f"MCP Tool: Вызов get_time_report для дат {start_date} - {end_date}, проект ID: {project_id if project_id else 'Все проекты'}...")

    report_data = await get_time_spent_report(api_key=USER_API_KEY, OPENPROJECT_URL=OPENPROJECT_URL, start_date=start_date,
                                        end_date=end_date, project_id=project_id)

    if not report_data:
        logger.error(f"Не удалось получить отчет о затраченном времени.", exc_info=True)
        return "Не удалось получить отчет о затраченном времени. Проверьте лог сервера для деталей или убедитесь, что есть данные за выбранный период."

    report_message = f"Отчет по затраченному времени с {start_date} по {end_date}"
    if project_id:
        report_message += f" для проекта ID: {project_id}"
    report_message += ":\n"

    if not report_data:
        report_message += "За этот период не найдено записей о затраченном времени."
    else:
        for user, data in report_data.items():
            report_message += f"\n  Пользователь: {user}"
            report_message += f"\n    Всего часов: {data['total_hours']:.2f}"
            if data['projects_data']:
                report_message += "\n    Детализация по проектам:"
                for project, hours in data['projects_data'].items():
                    report_message += f"\n      - {project}: {hours:.2f} часов"
            else:
                report_message += "\n    Нет данных по проектам."

    return report_message


if __name__ == "__main__":
    print("Инициализация MCP сервера для OpenProject...")
    print("Запуск MCP сервера...")
    mcp.run(transport='stdio')
