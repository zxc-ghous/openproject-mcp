import asyncio
import pathlib
import yaml
import os
import logging
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_gigachat import GigaChat
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from openproject import get_projects, pretty_projects
from datetime import datetime
from config import setup_logger
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

log_path = Path(r"logs/client.log")
logger = setup_logger('client', log_path)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()
prompts_path = PROJECT_ROOT / "prompts.yaml"
SERVER_MODULE_NAME = "mcp_server.openproject_server"
OPENPROJECT_URL = os.getenv("OPENPROJECT_URL")

with open(prompts_path, 'r', encoding='utf-8') as file:
    data = yaml.safe_load(file)

SYSTEM_PROMPT_TEMPLATE = data["system_prompt"]


class AgentManager:
    """
    Управляет жизненным циклом MCP-агентов для разных пользователей.
    Создает, кэширует и переиспользует агентов, чтобы избежать
    повторной инициализации при каждом сообщении.
    """

    def __init__(self):
        self._agents = {}  # thread_id -> agent
        self._sessions = {}  # thread_id -> ClientSession
        self._exit_stacks = {}  # thread_id -> AsyncExitStack
        self._locks = {}  # thread_id -> asyncio.Lock для предотвращения гонки состояний при создании агента

        # Эти компоненты являются общими для всех агентов
        self.model = GigaChat(model="GigaChat-2-Max", timeout=120)
        self.checkpointer = InMemorySaver()
        logger.info("AgentManager initialized.")

    async def _create_agent(self, api_key: str, thread_id: str):
        """
        Создает и инициализирует нового агента для указанного thread_id.
        Этот метод содержит логику, которая ранее была в run_mcp_agent.
        """
        logger.info(f"Creating new agent for thread_id: {thread_id}")
        if thread_id in self._agents:
            logger.warning(f"Agent for thread_id {thread_id} already exists. This should not happen.")
            return self._agents[thread_id]

        exit_stack = AsyncExitStack()
        self._exit_stacks[thread_id] = exit_stack

        try:
            # Параметры для запуска дочернего процесса MCP-сервера
            server_params = StdioServerParameters(
                command="python",
                args=["-m", SERVER_MODULE_NAME],
                cwd=str(PROJECT_ROOT),
                env={"OPENPROJECT_API_KEY": api_key, "OPENPROJECT_URL": OPENPROJECT_URL},
            )

            # Входим в контекст stdio_client и ClientSession с помощью exit_stack
            read, write = await exit_stack.enter_async_context(stdio_client(server_params))
            session = await exit_stack.enter_async_context(ClientSession(read, write))

            await session.initialize()
            logger.info(f"MCP session initialized for {thread_id}")

            tools = await load_mcp_tools(session)
            logger.info(f"Loaded {len(tools)} tools for {thread_id}")

            # Получаем и форматируем системный промпт
            projects_list = get_projects(api_key)
            projects_str = "\n".join(pretty_projects(projects_list))
            formated_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(projects=projects_str,
                                                                   current_date=datetime.today().strftime('%Y-%m-%d'))

            # Создаем агент
            agent_executor = create_react_agent(
                self.model,
                tools,
                checkpointer=self.checkpointer,
                prompt=formated_system_prompt
            )
            logger.info(f"Agent created for thread_id: {thread_id}")

            # Сохраняем сессию и агент
            self._sessions[thread_id] = session
            self._agents[thread_id] = agent_executor

            return agent_executor

        except Exception as e:
            logger.error(f"Failed to create agent for {thread_id}: {e}")
            # В случае ошибки создания, очищаем ресурсы
            await self._cleanup_agent(thread_id)
            raise  # Передаем исключение выше

    async def _get_or_create_agent(self, api_key: str, thread_id: str):
        """
        Возвращает существующий агент или создает новый, если его нет.
        Использует блокировку для предотвращения гонки состояний.
        """
        if thread_id not in self._agents:
            if thread_id not in self._locks:
                self._locks[thread_id] = asyncio.Lock()

            async with self._locks[thread_id]:
                # Повторная проверка, так как другой корутин мог уже создать агента, пока мы ждали блокировку
                if thread_id not in self._agents:
                    await self._create_agent(api_key, thread_id)

        return self._agents[thread_id]

    async def process_message(self, api_key: str, query: str, thread_id: str) -> str:
        """
        Обрабатывает сообщение пользователя, используя кэшированного агента.
        """
        if not api_key:
            return "Ошибка: API ключ не предоставлен."

        try:
            agent_executor = await self._get_or_create_agent(api_key, thread_id)

            config = {"configurable": {"thread_id": thread_id}}
            response = await agent_executor.ainvoke({"messages": [{"role": "user", "content": query}]}, config=config)

            final_content = "Не удалось извлечь ответ."
            if isinstance(response, dict) and "messages" in response and response["messages"]:
                # Последнее сообщение в списке обычно является ответом ассистента
                final_content = response["messages"][-1].content

            logger.info(f"Successfully processed message for {thread_id}")
            return final_content

        except Exception as e:
            logger.error(f"Critical error during message processing for {thread_id}: {e}")
            # При критической ошибке можно удалить агента, чтобы при следующем запросе он был создан заново
            await self._cleanup_agent(thread_id)
            return f"К сожалению, произошла внутренняя ошибка. Попробуйте снова.\n\nДетали: {e}"

    async def _cleanup_agent(self, thread_id: str):
        """Очищает ресурсы, связанные с агентом."""
        logger.info(f"Cleaning up agent and session for {thread_id}")
        if thread_id in self._exit_stacks:
            stack = self._exit_stacks.pop(thread_id)
            await stack.aclose()
        self._agents.pop(thread_id, None)
        self._sessions.pop(thread_id, None)
        self._locks.pop(thread_id, None)

    async def shutdown(self):
        """
        Корректно завершает работу всех активных сессий.
        Вызывать при остановке бота.
        """
        logger.info("Shutting down AgentManager and all active sessions...")
        for thread_id in list(self._exit_stacks.keys()):
            await self._cleanup_agent(thread_id)
        logger.info("AgentManager shutdown complete.")

# --- Использование ---
# В основном файле вашего бота создайте один экземпляр AgentManager
# agent_manager = AgentManager()
#
# И в обработчике сообщений вызывайте:
# response_text = await agent_manager.process_message(api_key, query, thread_id)
#
# При завершении работы бота не забудьте вызвать:
# await agent_manager.shutdown()
