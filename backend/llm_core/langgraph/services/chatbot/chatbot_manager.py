from langchain_core.messages import BaseMessage
from typing import Dict, List
import uuid
from rich import print as rprint
import asyncio

message_queue = asyncio.Queue()

class ChatbotManager:
    """Manages chatbots, stores and retreives old messages."""
    def __init__(self):
        self.chatbots: Dict[str, Dict[str, List[BaseMessage]]] = {}

    async def create_chatbot(self, session: str, language: str):
        """Creates a new chatbot."""
        if session in self.chatbots:
            rprint("Chatbot already exists for session: ", session)
            return

        thread_uuid = uuid.uuid4()
        config = {"configurable": {"thread_id": f"{thread_uuid}"}, "recursion_limit": 100}
        self.chatbots[session] = {
            "language": language,
            "config": config,
            "messages": {},
            "table_name": None,
            "pdf_name": None
        }


    async def set_table(self, session: str, table_name: str):
        """Sets the table name for the chatbot. Does not trigger the chat stream."""
        try:
            self.chatbots[session]["table_name"] = table_name
        except Exception as e:
            raise RuntimeError(f"Failed to add or replace Table name for session {session}: {e}")
        
        try:
            thread_id = self.chatbots[session]["config"]["configurable"]["thread_id"]
            if thread_id not in self.chatbots[session]["messages"]:
                self.chatbots[session]["messages"][thread_id] = {}
                self.chatbots[session]["messages"][thread_id][table_name] = None
            elif table_name not in self.chatbots[session]["messages"][thread_id]:
                self.chatbots[session]["messages"][thread_id][table_name] = None
        except Exception as e:
            raise RuntimeError(f"Failed to add or replace Table config for session {session}: {e}")
        

    async def set_pdf(self, session: str, pdf_name: str):
        """Sets the pdf name for the chatbot. Does not trigger the chat stream."""
        try:
            self.chatbots[session]["pdf_name"] = pdf_name
        except Exception as e:
            raise RuntimeError(f"Failed to add or replace PDF name for session {session}: {e}")
        
        try:
            thread_id = self.chatbots[session]["config"]["configurable"]["thread_id"]
            if thread_id not in self.chatbots[session]["messages"]:
                self.chatbots[session]["messages"][thread_id] = {}
                self.chatbots[session]["messages"][thread_id][pdf_name] = None
            elif pdf_name not in self.chatbots[session]["messages"][thread_id]:
                self.chatbots[session]["messages"][thread_id][pdf_name] = None
        except Exception as e:
            raise RuntimeError(f"Failed to add or replace PDF config for session {session}: {e}")


    async def get_chatbot(self, session_id: str):
        """Returns the chatbot for the session."""
        print(f"Getting chatbot for session: {session_id}: ", self.chatbots)
        if session_id not in self.chatbots:
            raise ValueError(f"No chatbot found for session '{session_id}'.")
        return self.chatbots[session_id]
    

    async def get_chatbot_table_name(self, session_id: str):
        """Returns the set table name for the chatbot."""
        if "table_name" not in self.chatbots[session_id]:
            return None
        return self.chatbots[session_id]["table_name"]
        

    async def get_chatbot_pdf_name(self, session_id: str):
        """Returns the set pdf name for the chatbot."""
        if "pdf_name" not in self.chatbots[session_id]:
            return None
        return self.chatbots[session_id]["pdf_name"]


async def start_chatbot(session: str, manager):
    if session not in manager.chatbots:
        await manager.create_chatbot(session, "English")


async def set_table(session: str, table_name: str, manager):
    await manager.set_table(session, table_name)


async def set_pdf(session: str, pdf_name: str, manager):
    await manager.set_pdf(session, pdf_name)