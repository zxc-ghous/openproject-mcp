import re
import datetime

def pretty_projects(projects):
    formatted_projects = []
    for project in projects:
        project_id = project.get('id', 'N/A')
        project_name = project.get('name', 'Без имени')
        project_status = project.get('_links', {}).get('status', {}).get('title', 'Статус неизвестен')
        # Получаем описание. Используем .get() для безопасного доступа к вложенным ключам
        project_description_raw = project.get('description', {}).get('raw', 'Без описания')
        formatted_projects.append(
            f"- ID: {project_id}, Название: **{project_name}**\n"
            f"  Описание: {project_description_raw}"
            f"  Статус: {project_status}"
        )
    return formatted_projects


def pretty_tasks(tasks: list) -> str:
    """
    Преобразует список словарей задач OpenProject в удобочитаемый строковый формат,
    включая название, описание, ответственного, затраченное время, статус,
    дату начала и дату окончания.

    Args:
        tasks (list): Список словарей, представляющих задачи OpenProject,
                      полученный из OpenProject API.

    Returns:
        str: Отформатированная строка со списком задач.
    """
    if not tasks:
        return "В проекте нет задач или не удалось получить информацию о них."

    formatted_output = []

    for task in tasks:
        # 1. ID задачи
        task_id = task.get('id', 'N/A')
        # 2. Название задачи (subject)
        subject = task.get('subject', 'Без названия')

        # 3. Описание (description)
        description_raw = task.get('description', {}).get('raw', 'Без описания')
        description = description_raw.strip() if description_raw else 'Без описания'

        # 4. Кто назначен ответственным (assignee)
        assignee_name = 'Не назначен'
        if '_links' in task and 'assignee' in task['_links'] and task['_links']['assignee']:
            assignee_name = task['_links']['assignee'].get('title', 'Неизвестно')

        # 5. Сколько уже времени было затрачено (spentTime)
        spent_time_iso = task.get('spentTime', 'PT0S')
        readable_spent_time = "0 секунд" # Значение по умолчанию

        # Парсинг ISO 8601 Duration (e.g., PT8H30M, PT1H, PT1M, PT30S)
        hours_match = re.search(r'(\d+)H', spent_time_iso)
        minutes_match = re.search(r'(\d+)M', spent_time_iso)
        seconds_match = re.search(r'(\d+)S', spent_time_iso)

        parts = []
        if hours_match:
            parts.append(f"{hours_match.group(1)} ч")
        if minutes_match:
            parts.append(f"{minutes_match.group(1)} мин")
        if seconds_match:
            parts.append(f"{seconds_match.group(1)} сек")

        if parts:
            readable_spent_time = ", ".join(parts)
        elif spent_time_iso == 'PT0S':
            readable_spent_time = "0 секунд"
        else:
            readable_spent_time = "Не указано"

        # 6. Текущий статус задачи (status)
        status_name = 'Статус неизвестен'
        if '_links' in task and 'status' in task['_links'] and task['_links']['status']:
            status_name = task['_links']['status'].get('title', 'Статус неизвестен')

        # 7. Дата начала задачи (startDate)
        start_date_str = task.get('startDate')
        if start_date_str:
            try:
                start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
            except ValueError:
                start_date = 'Неверный формат даты'
        else:
            start_date = 'Не указана'

        # 8. Дата окончания задачи (dueDate)
        due_date_str = task.get('dueDate')
        if due_date_str:
            try:
                due_date = datetime.datetime.strptime(due_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
            except ValueError:
                due_date = 'Неверный формат даты'
        else:
            due_date = 'Не указана'

        formatted_output.append(
            f"---"
            f" \n ID задачи: {task_id}"
            f" \n Название задачи: {subject}"
            f" \n Описание: {description}"
            f" \n Назначенный: {assignee_name}"
            f" \n Затраченное время: {readable_spent_time}"
            f" \n Статус: {status_name}"
            f" \n Дата начала: {start_date}" # Добавлено
            f" \n Дата окончания: {due_date}" # Добавлено
            f" \n ---"
        )
    return "\n".join(formatted_output)


def pretty_spent_time(report: dict):
    formated = []
    for user, data in report.items():
        formated.append(f"  {user}: Всего часов: {data['total_hours']:.2f}")
        for project, hours in data['projects_data'].items():
            formated.append(f"    - {project}: {hours:.2f} часов")
    return "\n".join(formated)


def convert_hours_to_iso8601_duration(hours: float) -> str:
    """
    Конвертирует часы (float) в формат длительности ISO 8601 (например, PT2H30M).

    Args:
        hours (float): Количество часов для конвертации.

    Returns:
        str: Строка длительности в формате ISO 8601.
    """
    if hours < 0:
        raise ValueError("Количество часов не может быть отрицательным.")

    total_minutes = int(hours * 60)

    if total_minutes == 0:
        return "PT0S"

    h = total_minutes // 60
    m = total_minutes % 60

    duration_parts = []
    if h > 0:
        duration_parts.append(f"{h}H")
    if m > 0:
        duration_parts.append(f"{m}M")

    # Изменено: Добавляем 'T' перед компонентами времени, если они есть.
    if duration_parts:
        return "P" + "T" + "".join(duration_parts)
    else:
        return "PT0S"

def convert_iso8601_duration_to_hours(iso_duration: str) -> float:
    """
    Преобразует строку длительности в формате ISO 8601 (например, "PT5H", "PT2H30M")
    в количество часов (float).

    Args:
        iso_duration (str): Строка длительности в формате ISO 8601.

    Returns:
        float: Количество часов.

    Raises:
        ValueError: Если формат строки не поддерживается.
    """
    if not iso_duration.startswith("PT"):
        raise ValueError("Неверный формат ISO 8601 Duration. Должен начинаться с 'PT'.")

    duration_str = iso_duration[2:] # Удаляем "PT"

    hours = 0.0
    minutes = 0.0

    # Разбираем часы
    hour_match = re.search(r'(\d+)H', duration_str)
    if hour_match:
        hours = float(hour_match.group(1))

    # Разбираем минуты
    minute_match = re.search(r'(\d+)M', duration_str)
    if minute_match:
        minutes = float(minute_match.group(1))

    return hours + (minutes / 60.0)