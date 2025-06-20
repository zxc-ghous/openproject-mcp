from openproject.format_utils import convert_hours_to_iso8601_duration, convert_iso8601_duration_to_hours
import logging
from dotenv import load_dotenv
import requests
import json
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import aiohttp
import asyncio
from config import setup_logger
from pathlib import Path

load_dotenv()

log_path = Path(r"logs")
logger = setup_logger('endpoints', log_path)


async def get_projects(api_key, OPENPROJECT_URL, page_size=100):
    """
    Асинхронно получает список всех проектов из OpenProject, обрабатывая пагинацию.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        OPENPROJECT_URL (str): Базовый URL до OpenProject инстанса.
        page_size (int): Количество проектов на одной странице.

    Returns:
        list: Список проектов (dict) или None в случае ошибки.
    """
    all_projects = []
    offset = 0
    total_projects = None

    headers = {
        "Content-Type": "application/json"
    }

    auth = aiohttp.BasicAuth("apikey", api_key)

    async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
        while True:
            url = f"{OPENPROJECT_URL}/api/v3/projects?offset={offset}&pageSize={page_size}"

            try:
                async with session.get(url, timeout=30) as response:
                    response.raise_for_status()
                    data = await response.json()

                    if total_projects is None:
                        total_projects = data.get("total")
                        print(f"Всего проектов доступно: {total_projects} (для текущего пользователя).")

                    current_page_projects = data.get("_embedded", {}).get("elements", [])
                    all_projects.extend(current_page_projects)

                    if len(current_page_projects) < page_size or len(all_projects) >= total_projects:
                        break

                    offset += page_size

            except aiohttp.ClientResponseError as http_err:
                print(f"HTTP ошибка: {http_err.status} — {http_err.message}")
                return None
            except aiohttp.ClientConnectorError as conn_err:
                print(f"Ошибка подключения: {conn_err}")
                return None
            except asyncio.TimeoutError:
                print("Время ожидания запроса истекло")
                return None
            except aiohttp.ClientError as req_err:
                print(f"Общая ошибка клиента: {req_err}")
                return None
            except json.JSONDecodeError as json_err:
                print(f"Ошибка декодирования JSON: {json_err}")
                return None

    return all_projects


async def update_work_package_dates(api_key: str, OPENPROJECT_URL: str, work_package_id: int,
                                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Асинхронно изменяет или удаляет (если передано "DELETE") начальную и/или конечную дату
    задачи (Work Package) в OpenProject, используя lockVersion.
    """
    # --- ШАГ 1: ИСПРАВЛЕННЫЙ ЗАГОЛОВОК ---
    # Используем Content-Type, который ожидает API OpenProject
    headers = {
        "Content-Type": "application/json"  # Оставляем application/json, так как тело запроса не содержит _links или _embedded.
                                            # Сервер должен сам корректно обработать это.
                                            # Если ошибка сохранится, попробуйте "application/hal+json", но обычно для PATCH
                                            # простого json достаточно. Главное - это получать ответ.
    }
    auth = aiohttp.BasicAuth("apikey", api_key)

    async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
        # --- Блок для получения lockVersion (остается без изменений) ---
        get_url = f"{OPENPROJECT_URL}/api/v3/work_packages/{work_package_id}"
        try:
            async with session.get(get_url, timeout=30) as get_response:
                get_response.raise_for_status()
                current_work_package_data = await get_response.json()
                lock_version = current_work_package_data.get("lockVersion")

                if lock_version is None:
                    logger.warning(f"Не удалось получить lockVersion для задачи ID: {work_package_id}. Обновление невозможно.")
                    return None
        except Exception as e:
            logger.exception(f"Произошла ошибка при получении lockVersion для задачи ID {work_package_id}.")
            return None

        # --- Формируем тело PATCH запроса (остается без изменений) ---
        payload: Dict[str, Any] = {
            "lockVersion": lock_version
        }
        if start_date is not None:
            payload["startDate"] = None if start_date == "DELETE" else start_date
        if end_date is not None:
            # В API OpenProject поле конечной даты называется 'dueDate'
            payload["dueDate"] = None if end_date == "DELETE" else end_date

        if len(payload) == 1:
            logger.info(f"Для задачи ID {work_package_id} не указаны даты для изменения или удаления. Никаких действий не выполнено.")
            # Возвращаем данные без изменений, а не строку
            return current_work_package_data

        # --- ШАГ 2: БЛОК ДЛЯ ОБНОВЛЕНИЯ С ДЕТАЛЬНЫМ ЛОГИРОВАНИЕМ ОШИБКИ ---
        update_url = f"{OPENPROJECT_URL}/api/v3/work_packages/{work_package_id}"
        try:
            async with session.patch(update_url, json=payload, timeout=30) as response:
                if not response.ok:
                    error_details = await response.text()
                    logger.error(
                        f"Ошибка обновления задачи ID {work_package_id}. "
                        f"Статус: {response.status}. URL: {response.url}. "
                        f"Отправляемые данные: {payload}. " # Добавлено логгирование отправляемых данных
                        f"Детали от сервера: {error_details}"
                    )
                response.raise_for_status()
                data = await response.json()
                logger.info(f"Успешно обновлена задача ID: {work_package_id}")
                return data
        except aiohttp.ClientResponseError:
            # Мы уже залогировали подробности выше, так что здесь можно просто вернуть None
            return None
        except Exception as e:
            logger.exception(f"Произошла общая ошибка при обновлении задачи ID {work_package_id}.")
            return None


async def create_task(api_key: str, OPENPROJECT_URL: str, project_id: int, subject: str,
                      description: Optional[str] = None, type_id: int = 1,
                      status_id: int = 1, priority_id: int = 2) -> Optional[Dict[str, Any]]:
    """
    Асинхронно создает новую задачу (Work Package) в OpenProject.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        OPENPROJECT_URL (str): Базовый URL OpenProject.
        project_id (int): ID проекта, в котором будет создана задача.
        subject (str): Заголовок задачи.
        description (str, optional): Описание задачи.
        type_id (int): ID типа задачи.
        status_id (int): ID статуса задачи.
        priority_id (int): ID приоритета задачи.

    Returns:
        Optional[Dict[str, Any]]: Созданная задача или None при ошибке.
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

    auth = aiohttp.BasicAuth("apikey", api_key)

    async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
        try:
            async with session.post(url, json=payload, timeout=30) as response:
                response.raise_for_status()
                new_task = await response.json()
                print(f"Задача '{new_task.get('subject')}' успешно создана с ID: {new_task.get('id')}")
                return new_task

        except aiohttp.ClientResponseError as http_err:
            print(f"Ошибка HTTP при создании задачи: {http_err.status} — {http_err.message}")
        except aiohttp.ClientConnectorError as conn_err:
            print(f"Ошибка подключения: {conn_err}")
        except asyncio.TimeoutError:
            print("Время ожидания запроса истекло")
        except aiohttp.ClientError as req_err:
            print(f"Общая ошибка клиента: {req_err}")
        except json.JSONDecodeError as json_err:
            print(f"Ошибка декодирования JSON: {json_err}")
            return None

    return None


async def get_project_tasks(api_key: str, OPENPROJECT_URL: str, project_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Асинхронно получает список задач (Work Packages) для указанного проекта в OpenProject.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        OPENPROJECT_URL (str): Базовый URL OpenProject.
        project_id (int): ID проекта, для которого нужно получить задачи.

    Returns:
        list: Список словарей, представляющих задачи проекта, если успешно,
              или пустой список, если задач нет, или None при ошибке.
    """
    url = f"{OPENPROJECT_URL}/api/v3/projects/{project_id}/work_packages"
    headers = {
        "Content-Type": "application/json"
    }
    auth = aiohttp.BasicAuth("apikey", api_key)

    async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
        try:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                data = await response.json()
                tasks = data.get('_embedded', {}).get('elements', [])

                if tasks:
                    print(f"Успешно получен список из {len(tasks)} задач для проекта ID: {project_id}")
                else:
                    print(f"В проекте ID: {project_id} задачи не найдены.")
                return tasks

        except aiohttp.ClientResponseError as http_err:
            print(f"Ошибка HTTP при получении задач: {http_err.status} — {http_err.message}")
        except aiohttp.ClientConnectorError as conn_err:
            print(f"Ошибка подключения: {conn_err}")
        except asyncio.TimeoutError:
            print("Время ожидания запроса истекло")
        except aiohttp.ClientError as req_err:
            print(f"Общая ошибка клиента: {req_err}")
        except json.JSONDecodeError as json_err:
            print(f"Ошибка декодирования JSON: {json_err}")
            return None

    return None


async def log_time_on_task(
    api_key: str,
    OPENPROJECT_URL: str,
    task_id: int,
    hours: float,
    comment: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Асинхронно регистрирует затраченное время на выполнение задачи (Work Package) в OpenProject.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        OPENPROJECT_URL (str): Базовый URL OpenProject.
        task_id (int): ID задачи, на которую регистрируется время.
        hours (float): Количество затраченных часов.
        comment (str, optional): Комментарий к записи времени.

    Returns:
        dict: Данные о созданной записи времени, или None при ошибке.
    """
    url = f"{OPENPROJECT_URL}/api/v3/time_entries"

    # Преобразуем часы в ISO 8601 Duration
    try:
        iso_duration = convert_hours_to_iso8601_duration(hours)
    except ValueError as ve:
        print(f"Ошибка при преобразовании времени: {ve}")
        return None

    payload: Dict[str, Any] = {
        "spentOn": date.today().isoformat(),
        "hours": iso_duration,
        "_links": {
            "workPackage": {"href": f"/api/v3/work_packages/{task_id}"}
        }
    }
    if comment:
        payload["comment"] = {"raw": comment}

    headers = {"Content-Type": "application/json"}
    auth = aiohttp.BasicAuth("apikey", api_key)

    async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
        try:
            async with session.post(url, json=payload, timeout=30) as resp:
                resp.raise_for_status()
                entry = await resp.json()
                print(f"Успешно зарегистрировано {hours}h на задаче {task_id}")
                return entry

        except aiohttp.ClientResponseError as e:
            print(f"HTTP ошибка при логировании времени: {e.status} — {e.message}")
        except aiohttp.ClientConnectorError as e:
            print(f"Ошибка подключения: {e}")
        except asyncio.TimeoutError:
            print("Время ожидания запроса истекло")
        except aiohttp.ClientError as e:
            print(f"Общая ошибка клиента: {e}")
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON: {e}")
            return None

    return None


async def get_time_spent_report(
    api_key: str,
    OPENPROJECT_URL: str,
    start_date: str,
    end_date: str,
    project_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Асинхронно формирует отчет по затраченному времени за указанный промежуток,
    с возможностью фильтрации по проекту.

    Args:
        api_key (str): API ключ пользователя OpenProject.
        OPENPROJECT_URL (str): Базовый URL OpenProject.
        start_date (str): Начальная дата 'YYYY-MM-DD'.
        end_date (str): Конечная дата 'YYYY-MM-DD'.
        project_id (int, optional): ID проекта для фильтрации.

    Returns:
        dict: Отчет по пользователям и проектам, или None при ошибке.
    """
    # Валидация дат
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        if start_dt > end_dt:
            print("Ошибка: начальная дата позже конечной.")
            return None
    except ValueError:
        print("Ошибка формата даты. Используйте YYYY-MM-DD.")
        return None

    url = f"{OPENPROJECT_URL}/api/v3/time_entries"
    headers = {"Content-Type": "application/json"}
    auth = aiohttp.BasicAuth("apikey", api_key)

    report: Dict[str, Any] = {}
    all_entries = []
    offset = 0
    page_size = 100

    async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
        while True:
            # Собираем фильтры
            filters = [
                {"spentOn": {"operator": "<>d", "values": [start_date, end_date]}}
            ]
            if project_id is not None:
                filters.append({"project": {"operator": "=", "values": [str(project_id)]}})

            params = {
                "offset": offset,
                "pageSize": page_size,
                "filters": json.dumps(filters)
            }

            try:
                async with session.get(url, params=params, timeout=30) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            except aiohttp.ClientResponseError as e:
                print(f"HTTP ошибка при получении записей: {e.status} — {e.message}")
                return None
            except aiohttp.ClientConnectorError as e:
                print(f"Ошибка подключения: {e}")
                return None
            except asyncio.TimeoutError:
                print("Время ожидания добило")
                return None
            except aiohttp.ClientError as e:
                print(f"Клиентская ошибка: {e}")
                return None
            except json.JSONDecodeError as e:
                print(f"Ошибка JSON: {e}")
                return None

            batch = data.get("_embedded", {}).get("elements", [])
            total = data.get("total", 0)
            count = data.get("count", 0)

            all_entries.extend(batch)
            if offset + count >= total:
                break
            offset += page_size

    # Формируем отчет
    for entry in all_entries:
        try:
            user = entry.get("_links", {}).get("user", {}).get("title")
            project = entry.get("_links", {}).get("project", {}).get("title")
            hours_iso = entry.get("hours")
            if not (user and project and hours_iso):
                print(f"Пропущена неполная запись: {entry}")
                continue

            hours = convert_iso8601_duration_to_hours(hours_iso)

            if user not in report:
                report[user] = {"total_hours": 0.0, "projects_data": {}}
            report[user]["total_hours"] += hours
            report[user]["projects_data"].setdefault(project, 0.0)
            report[user]["projects_data"][project] += hours

        except ValueError as ve:
            print(f"Ошибка конвертации: {ve} в записи: {entry}")
        except Exception as e:
            print(f"Неизвестная ошибка: {e} в записи: {entry}")

    return report


if __name__ == "__main__":
    from openproject.format_utils import pretty_spent_time

    TARGET_ID = 50
    task_id = 667
    kkk = "4e93bcc9c4dff6304f2dc31b7b76bb9e3ba96c9c6ba4a8c2cbd0ea363bf8047c"
    start_date_str = "2025-05-12"
    end_date_str = "2025-06-11"
    report_specific_project = get_time_spent_report(kkk, start_date_str, end_date_str, 19)
    print(pretty_spent_time(report_specific_project))
