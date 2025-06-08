import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

OPENPROJECT_URL = os.environ["OPENPROJECT_URL"]


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

            # В рабочем боте эти print'ы можно убрать или заменить на логирование
            print(
                f"Получено {len(current_page_projects)} проектов на странице (offset: {offset}). Всего получено: {len(all_projects)}")

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
