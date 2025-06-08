import asyncio
import pathlib

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_gigachat import GigaChat
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
import yaml
load_dotenv()

# Динамически определяем корень проекта.
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()
prompts_path = PROJECT_ROOT / "prompts.yaml"
SERVER_MODULE_NAME = "mcp_server.openproject_server"

with open(prompts_path, 'r', encoding='utf-8') as file:
    data = yaml.safe_load(file)

system_prompt = data["system_prompt"]



model = GigaChat(model="GigaChat-2-Max")
checkpointer = InMemorySaver()

async def run_mcp_agent(api_key: str, query: str, thread_id: str) -> str:
    """
    Запускает MCP сессию с агентом для выполнения одного запроса.

    Args:
        api_key: API ключ пользователя OpenProject.
        query: Запрос пользователя для агента.

    Returns:
        Ответ от агента в виде строки.
    """
    if not api_key:
        return "Ошибка: API ключ не предоставлен. Невозможно запустить MCP сессию."

    server_params = StdioServerParameters(
        command="python",
        args=["-m", SERVER_MODULE_NAME],
        cwd=str(PROJECT_ROOT),
        env={"OPENPROJECT_API_KEY": api_key},
    )
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                agent = create_react_agent(model, tools, checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}
                response = await agent.ainvoke({"messages": [{"role": "user", "content": query}]},
                                               config=config)
                # TODO: почему то при передачи system prompt падает с ошибкой.
                #       и вообще етот  create_react_agent мне не особо нравится

                final_content = "Не удалось извлечь ответ."
                if isinstance(response, dict) and "messages" in response and response["messages"]:
                    final_content = response["messages"][-1].content

                print("MCP сессия успешно завершена.")
                return final_content

    except Exception as e:
        print(f"Критическая ошибка в MCP сессии: {e}")
        return f"К сожалению, произошла внутренняя ошибка при обработке вашего запроса. Попробуйте позже.\n\nДетали: {e}"
