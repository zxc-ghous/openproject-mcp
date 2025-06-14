# logging_config.py

import logging
import sys

def setup_logger(name, log_file, level=logging.INFO):
    """Функция для настройки и получения логгера."""

    # Создаем обработчик, который будет записывать логи в файл
    handler = logging.FileHandler(log_file, encoding='utf-8')
    # Устанавливаем формат записей: ВРЕМЯ - ИМЯ_ЛОГГЕРА - УРОВЕНЬ - СООБЩЕНИЕ
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Создаем объект логгера
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Проверяем, есть ли у логгера уже обработчики, чтобы не добавлять их многократно
    if not logger.handlers:
        logger.addHandler(handler)
        # Если нужно выводить логи еще и в консоль (для отладки), раскомментируйте строки ниже
        # stream_handler = logging.StreamHandler(sys.stdout)
        # stream_handler.setFormatter(formatter)
        # logger.addHandler(stream_handler)


    return logger