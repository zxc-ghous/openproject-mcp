import logging
from pathlib import Path
from datetime import datetime
import sys

def setup_logger(name, base_log_path, level=logging.INFO):
    """
    Функция для настройки и получения логгера.
    Создает папку с сегодняшней датой и добавляет время к имени лог-файла.
    """
    # Создаем имя папки с текущей датой
    today_folder = datetime.now().strftime("%Y-%m-%d")
    # Формируем полный путь к папке логов
    log_folder_path = Path(base_log_path) / today_folder
    # Создаем папку, если она не существует
    log_folder_path.mkdir(parents=True, exist_ok=True)

    # Создаем имя файла лога с текущим временем
    current_time = datetime.now().strftime("%H-%M-%S")
    log_file_name = f"{name}_{current_time}.log"
    full_log_file_path = log_folder_path / log_file_name

    # Создаем обработчик, который будет записывать логи в файл
    handler = logging.FileHandler(full_log_file_path, encoding='utf-8')
    # Устанавливаем формат записей: ВРЕМЯ - ИМЯ_ЛОГГЕРА - УРОВЕНЬ - СООБЩЕНИЕ
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Создаем объект логгера
    logger = logging.getLogger(name)
    logger.setLevel(level)

    logger.addHandler(handler)

    # Если нужно выводить логи еще и в консоль (для отладки), раскомментируйте строки ниже
    # stream_handler = logging.StreamHandler(sys.stdout)
    # stream_handler.setFormatter(formatter)
    # logger.addHandler(stream_handler)

    return logger