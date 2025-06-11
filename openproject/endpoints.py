from openproject.format_utils import convert_hours_to_iso8601_duration, convert_iso8601_duration_to_hours
import logging
from dotenv import load_dotenv
import requests
import json
import os
from datetime import datetime, date
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")
if not OPENPROJECT_URL:
    logger.error("Переменная окружения OPENPROJECT_URL не установлена. Запросы к OpenProject могут не работать.")


def get_projects(api_key, page_size=100):
    """
    Получает список всех проектов из OpenProject, обрабатывая пагинацию,
    для указанного API ключа. OPENPROJECT_URL берется из переменной окружения.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        page_size (int): Количество проектов на одной странице. Максимально рекомендуемое 100-250.

    Returns:
        list: Список словарей, представляющих проекты, или None в случае ошибки.
    """
    all_projects = []
    offset = 0
    total_projects = None

    headers = {
        "Content-Type": "application/json"
    }

    while True:
        url = f"{OPENPROJECT_URL}/api/v3/projects?offset={offset}&pageSize={page_size}"

        try:
            response = requests.get(url, auth=("apikey", api_key), headers=headers)
            response.raise_for_status()
            data = response.json()

            if total_projects is None:
                total_projects = data.get("total")
                # В рабочем боте эти print'ы можно убрать или заменить на логирование
                print(f"Всего проектов доступно: {total_projects} (для текущего пользователя).")

            current_page_projects = data.get("_embedded", {}).get("elements", [])
            all_projects.extend(current_page_projects)


            if len(current_page_projects) < page_size or len(all_projects) >= total_projects:
                break

            offset += page_size

        except requests.exceptions.HTTPError as http_err:
            print(f"Ошибка HTTP при получении проектов: {http_err}")
            print(f"Ответ сервера: {response.text}")
            return None
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Ошибка подключения: {conn_err}")
            return None
        except requests.exceptions.Timeout as timeout_err:
            print(f"Время ожидания запроса истекло: {timeout_err}")
            return None
        except requests.exceptions.RequestException as req_err:
            print(f"Произошла другая ошибка: {req_err}")
            return None
        except json.JSONDecodeError as json_err:
            print(f"Ошибка декодирования JSON: {json_err}")
            print(f"Не удалось декодировать: {response.text}")
            return None

    return all_projects

# TODO: добавить назначение ответственных и срок выполнения задачи
def create_task(api_key, project_id, subject, description=None, type_id=1, status_id=1, priority_id=2):
    """
    Создает новую задачу (Work Package) в OpenProject в указанном проекте,
    для указанного API ключа. OPENPROJECT_URL берется из переменной окружения.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        project_id (int): ID проекта, в котором будет создана задача.
        subject (str): Заголовок (название) задачи.
        description (str, optional): Описание задачи. По умолчанию None.
        type_id (int, optional): ID типа задачи. По умолчанию 1 (Task).
        status_id (int, optional): ID статуса задачи. По умолчанию 1 (New).
        priority_id (int, optional): ID приоритета задачи. По умолчанию 2 (Normal).

    Returns:
        dict: Словарь с данными о созданной задаче, если успешно, иначе None.
    """
    url = f"{OPENPROJECT_URL}/api/v3/projects/{project_id}/work_packages"

    payload = {
        "subject": subject,
        "_links": {
            "type": {
                "href": f"/api/v3/types/{type_id}"
            },
            "status": {
                "href": f"/api/v3/statuses/{status_id}"
            },
            "priority": {
                "href": f"/api/v3/priorities/{priority_id}"
            },
            "project": {
                "href": f"/api/v3/projects/{project_id}"
            }
        }
    }

    if description:
        payload["description"] = {
            "raw": description
        }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, auth=("apikey", api_key), headers=headers, data=json.dumps(payload))
        response.raise_for_status()

        new_task = response.json()
        print(f"Задача '{new_task.get('subject')}' успешно создана с ID: {new_task.get('id')}")
        return new_task

    except requests.exceptions.HTTPError as http_err:
        print(f"Ошибка HTTP при создании задачи: {http_err}")
        print(f"Ответ сервера: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Ошибка подключения: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Время ожидания запроса истекло: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Произошла другая ошибка: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"Ошибка декодирования JSON: {json_err}")
        print(f"Не удалось декодировать: {response.text}")

    return None

def get_project_tasks(api_key: str, project_id: int) -> list | None:
    """
    Получает список задач (Work Packages) для указанного проекта в OpenProject.
    OPENPROJECT_URL берется из переменной окружения.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        project_id (int): ID проекта, для которого нужно получить задачи.

    Returns:
        list: Список словарей, представляющих задачи проекта, если успешно,
              иначе None.
    """
    url = f"{OPENPROJECT_URL}/api/v3/projects/{project_id}/work_packages"

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, auth=("apikey", api_key), headers=headers)
        response.raise_for_status() # Вызывает исключение для HTTP ошибок (4xx или 5xx)

        data = response.json()
        tasks = data.get('_embedded', {}).get('elements', [])

        if tasks:
            print(f"Успешно получен список из {len(tasks)} задач для проекта ID: {project_id}")
            return tasks
        else:
            print(f"В проекте ID: {project_id} задачи не найдены или произошла ошибка.")
            return [] # Возвращаем пустой список, если задач нет

    except requests.exceptions.HTTPError as http_err:
        print(f"Ошибка HTTP при получении задач: {http_err}")
        print(f"Ответ сервера: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Ошибка подключения: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Время ожидания запроса истекло: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Произошла другая ошибка запроса: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"Ошибка декодирования JSON: {json_err}")
        print(f"Не удалось декодировать: {response.text}")

    return None

def log_time_on_task(api_key: str, task_id: int, hours: float, comment: str = None) -> dict | None:
    """
    Регистрирует затраченное время на выполнение задачи (Work Package) в OpenProject.
    OPENPROJECT_URL берется из переменной окружения.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        task_id (int): ID задачи, на которую регистрируется время.
        hours (float): Количество затраченных часов (может быть дробным, например, 2.5 для 2 часов 30 минут).
        comment (str, optional): Комментарий к записи времени. По умолчанию None.

    Returns:
        dict: Словарь с данными о созданной записи времени, если успешно, иначе None.
    """
    url = f"{OPENPROJECT_URL}/api/v3/time_entries"

    # Преобразование часов в формат ISO 8601 Duration
    try:
        iso_duration = convert_hours_to_iso8601_duration(hours)
    except ValueError as val_err:
        print(f"Ошибка при преобразовании времени: {val_err}")
        return None

    payload = {
        "spentOn": date.today().isoformat(), # Текущая дата в формате YYYY-MM-DD
        "hours": iso_duration,
        "_links": {
            "workPackage": {
                "href": f"/api/v3/work_packages/{task_id}"
            }
            # Для регистрации времени, OpenProject API обычно автоматически связывает запись
            # с пользователем, чей API-ключ используется для аутентификации.
            # Явное указание "_links.user" обычно не требуется, если ключ принадлежит пользователю.
        }
    }

    if comment:
        payload["comment"] = {
            "raw": comment
        }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, auth=("apikey", api_key), headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Вызывает исключение для HTTP ошибок (4xx или 5xx)

        time_entry = response.json()
        return time_entry

    except requests.exceptions.HTTPError as http_err:
        print(f"Ошибка HTTP при регистрации времени: {http_err}")
        print(f"Ответ сервера: {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Ошибка подключения: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Время ожидания запроса истекло: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Произошла другая ошибка: {req_err}")
    except json.JSONDecodeError as json_err:
        print(f"Ошибка декодирования JSON: {json_err}")
        print(f"Не удалось декодировать: {response.text}")

    return None

def get_time_spent_report(api_key: str, start_date: str, end_date: str, project_id: int = None) -> dict | None:
    """
    Формирует отчет по затраченному времени за определенный промежуток времени,
    используя OpenProject API. OPENPROJECT_URL берется из переменной окружения.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        start_date (str): Начальная дата в формате 'YYYY-MM-DD'.
        end_date (str): Конечная дата в формате 'YYYY-MM-DD'.
        project_id (int, optional): ID проекта для фильтрации. Если не указан,
                                     возвращается общее время по всем проектам.
                                     По умолчанию None.

    Returns:
        dict: Словарь с отчетом по затраченному времени, сгруппированный по пользователям
              и проектам, если успешно, иначе None.
              Пример структуры отчета:
              {
                  'User Name 1': {
                      'total_hours': 15.5,
                      'projects_data': {
                          'Project A': 10.0,
                          'Project B': 5.5
                      }
                  },
                  'User Name 2': {
                      'total_hours': 8.0,
                      'projects_data': {
                          'Project C': 8.0
                      }
                  }
              }
    """
    url = f"{OPENPROJECT_URL}/api/v3/time_entries"
    report = {}
    all_time_entries = []
    offset = 0
    page_size = 100 # Установим разумный размер страницы для пагинации

    headers = {
        "Content-Type": "application/json"
    }

    # Валидация дат
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        if start_dt > end_dt:
            print("Ошибка: Начальная дата не может быть позже конечной даты.")
            return None
    except ValueError:
        print("Ошибка: Неверный формат даты. Используйте 'YYYY-MM-DD'.")
        return None

    while True:
        filters_list = []
        # Фильтр по диапазону дат
        # Изменяем оператор с "><" на "<>d" согласно документации OpenProject для "between days"
        filters_list.append({"spentOn": {"operator": "<>d", "values": [start_date, end_date]}})

        if project_id:
            # Фильтр по ID проекта
            # ID проекта должен быть строкой в списке значений.
            filters_list.append({"project": {"operator": "=", "values": [str(project_id)]}})

        params = {
            "offset": offset,
            "pageSize": page_size,
            "filters": json.dumps(filters_list)
        }

        try:
            response = requests.get(url, auth=("apikey", api_key), headers=headers, params=params)
            response.raise_for_status() # Вызывает исключение для HTTP ошибок (4xx или 5xx)

            response_json = response.json()
            time_entries = response_json.get("_embedded", {}).get("elements", [])
            all_time_entries.extend(time_entries)

            total = response_json.get("total", 0)
            count = response_json.get("count", 0)

            # Если текущий offset + количество полученных записей >= общему количеству,
            # значит, все данные получены, и можно выйти из цикла пагинации.
            if offset + count >= total:
                break
            else:
                offset += page_size # Переходим на следующую страницу

        except requests.exceptions.HTTPError as http_err:
            print(f"Ошибка HTTP при получении записей времени: {http_err}")
            print(f"Ответ сервера: {response.text}")
            return None
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Ошибка подключения: {conn_err}")
            return None
        except requests.exceptions.Timeout as timeout_err:
            print(f"Время ожидания запроса истекло: {timeout_err}")
            return None
        except requests.exceptions.RequestException as req_err:
            print(f"Произошла другая ошибка: {req_err}")
            return None
        except json.JSONDecodeError as json_err:
            print(f"Ошибка декодирования JSON: {json_err}")
            print(f"Не удалось декодировать: {response.text}")
            return None

    # Обработка полученных записей времени и формирование отчета
    for entry in all_time_entries:
        try:
            user_name = entry.get("_links", {}).get("user", {}).get("title")
            project_title = entry.get("_links", {}).get("project", {}).get("title")
            hours_iso = entry.get("hours")
            spent_on_str = entry.get("spentOn")

            # Проверяем наличие всех необходимых данных в записи
            if not all([user_name, project_title, hours_iso, spent_on_str]):
                print(f"Предупреждение: Пропущена запись из-за отсутствующих данных: {entry}")
                continue

            # Конвертируем ISO длительность в часы (float)
            hours = convert_iso8601_duration_to_hours(hours_iso)

            # Инициализируем структуру отчета для пользователя, если он еще не добавлен
            if user_name not in report:
                report[user_name] = {
                    'total_hours': 0.0,
                    'projects_data': {}
                }

            # Обновляем общее количество часов для пользователя
            report[user_name]['total_hours'] += hours
            # Обновляем количество часов для конкретного проекта этого пользователя
            report[user_name]['projects_data'][project_title] = report[user_name]['projects_data'].get(project_title, 0.0) + hours

        except ValueError as ve:
            print(f"Ошибка при обработке записи времени (конвертация часов/даты): {ve} - Запись: {entry}")
        except Exception as e:
            print(f"Неизвестная ошибка при обработке записи времени: {e} - Запись: {entry}")

    return report



if __name__=="__main__":
    from openproject.format_utils import pretty_spent_time
    TARGET_ID = 50
    task_id = 667
    kkk = "4e93bcc9c4dff6304f2dc31b7b76bb9e3ba96c9c6ba4a8c2cbd0ea363bf8047c"
    start_date_str = "2025-05-12"
    end_date_str = "2025-06-11"
    report_specific_project = get_time_spent_report(kkk, start_date_str, end_date_str, 19)
    print(pretty_spent_time(report_specific_project))
