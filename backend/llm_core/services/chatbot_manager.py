from langchain_core.messages import BaseMessage
from typing import Dict, List, Optional
from uuid import uuid4
from rich import print as rprint
import asyncio

message_queue = asyncio.Queue()

class ChatbotState:
    def __init__(self):
        self.thread_id  = str(uuid4())
        self.framework: str | None = None
        self.variables:  Dict[str, Optional[str]] = {}
        self.messages:   Dict[str, List[BaseMessage]] = {}

    # rename for clarity (optional)
    def set_var(self, key: str, value: Optional[str]):
        self.variables[key] = value
        if value and value not in self.messages:
            self.messages[value] = []

    get_var  = lambda self, key: self.variables.get(key)
    add_msg  = lambda self, ctx, m: self.messages.setdefault(ctx, []).append(m)
    get_msgs = lambda self, ctx: self.messages.get(ctx, [])


class ChatbotManager:
    def __init__(self):
        self.chatbots: Dict[str, ChatbotState] = {}

    async def ensure_state(self, session: str) -> ChatbotState:
        """Fetch or lazily create state in one call."""
        if session not in self.chatbots:
            self.chatbots[session] = ChatbotState()
        return self.chatbots[session]

    async def set_var(self, session: str, key: str, value: Optional[str]):
        (await self.ensure_state(session)).set_var(key, value)

    async def set_table(self, session: str, table_name: Optional[str]):
        await self.set_var(session, "table_name", table_name)

    async def set_pdf(self, session: str, pdf_name: Optional[str]):
        await self.set_var(session, "pdf_name", pdf_name)

    async def get_var(self, session: str, key: str):
        return (await self.ensure_state(session)).get_var(key)

    async def get_table_name(self, session: str):
        return await self.get_var(session, "table_name")

    async def get_pdf_name(self, session: str):
        return await self.get_var(session, "pdf_name")

    async def get_framework(self, session: str):
        return (await self.ensure_state(session)).framework

    async def set_framework(self, session: str, framework: str):
        (await self.ensure_state(session)).framework = framework

    async def add_message(self, session: str, ctx: str, msg: BaseMessage):
        (await self.ensure_state(session)).add_msg(ctx, msg)
