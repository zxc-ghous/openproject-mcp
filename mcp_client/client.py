from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_gigachat import GigaChat
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
import asyncio
import os
from dotenv import load_dotenv
import pathlib

load_dotenv()
# --- НАСТРОЙКА ПУТЕЙ ---
# Динамически определяем корень проекта.
# Это предполагает, что client.py находится в подпапке 'mcp_client'.
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()
# Указываем путь к серверу как к модулю
SERVER_MODULE_NAME = "mcp_server.openproject_server"

print(f"Корень проекта определен как: {PROJECT_ROOT}")
print(f"Сервер будет запущен как модуль: {SERVER_MODULE_NAME}")

api_key_for_server = os.getenv("OPENPROJECT_API_KEY")
if not api_key_for_server:
    # Если переменная не установлена, запросим ее у пользователя для этого сеанса
    api_key_for_server = input("Введите ваш OpenProject API ключ для этого сеанса: ").strip()

if not api_key_for_server:
    print("Ключ API не предоставлен. Выход.")
    exit(1)

server_params = StdioServerParameters(
    command="python",
    # Изменено: запускаем сервер как модуль, чтобы работали импорты
    args=["-m", SERVER_MODULE_NAME],
    # Изменено: устанавливаем рабочий каталог в корень проекта
    cwd=str(PROJECT_ROOT),
    # Передаем API ключ как переменную окружения
    env={"OPENPROJECT_API_KEY": api_key_for_server},
)

model = GigaChat(model="GigaChat-2-Max")


async def main():
    print("Запуск MCP клиента...")
    async with stdio_client(server_params) as (read, write):
        print("Клиент успешно подключился к подпроцессу сервера.")
        async with ClientSession(read, write) as session:
            # Инициализация соединения
            await session.initialize()
            print("Сессия MCP инициализирована.")

            # Получение инструментов
            tools = await load_mcp_tools(session)
            print(f"Загружены инструменты: {[tool.name for tool in tools]}")

            # Создание и запуск агента
            agent = create_react_agent(model, tools)
            print("Агент создан. Введите 'quit' для выхода.")

            while True:
                try:
                    query = input("\nQuery: ").strip()

                    if query.lower() == 'quit':
                        break

                    response = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
                    print("\nОтвет:")
                    # Выводим финальный ответ из словаря
                    if isinstance(response, dict) and "messages" in response:
                        print(response["messages"][-1].content)
                    else:
                        print(response)

                except Exception as e:
                    print(f"\nПроизошла ошибка: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
