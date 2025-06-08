import sqlite3
import pathlib

# Определяем путь к базе данных внутри папки telegram_app
DB_PATH = pathlib.Path(__file__).parent / "users.db"

def init_db():
    """Инициализирует базу данных и создает таблицу, если она не существует."""
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        # Создаем таблицу для хранения user_id и их api_key
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                api_key TEXT NOT NULL
            )
        ''')
        con.commit()
        con.close()
        print("База данных успешно инициализирована.")
    except sqlite3.Error as e:
        print(f"Ошибка при инициализации БД: {e}")

def save_api_key(user_id: int, api_key: str):
    """Сохраняет или обновляет API ключ для пользователя."""
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        # Используем INSERT OR REPLACE для добавления нового или обновления существующего ключа
        cur.execute("INSERT OR REPLACE INTO users (user_id, api_key) VALUES (?, ?)", (user_id, api_key))
        con.commit()
        con.close()
        print(f"API ключ для пользователя {user_id} сохранен.")
    except sqlite3.Error as e:
        print(f"Ошибка при сохранении ключа для пользователя {user_id}: {e}")

def get_api_key(user_id: int) -> str | None:
    """Получает API ключ для пользователя."""
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("SELECT api_key FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        con.close()
        if result:
            print(f"Найден ключ для пользователя {user_id}.")
            return result[0]
        else:
            print(f"Ключ для пользователя {user_id} не найден.")
            return None
    except sqlite3.Error as e:
        print(f"Ошибка при получении ключа для пользователя {user_id}: {e}")
        return None