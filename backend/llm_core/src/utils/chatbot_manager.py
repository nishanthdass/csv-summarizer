from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, AIMessageChunk
from typing import Dict, List
from db.tabular.postgres_utilities import get_all_columns_and_types
import uuid
from rich import print as rprint
import asyncio

message_queue = asyncio.Queue()

class ChatbotManager:
    """Manages chatbots, stores and retreives old messages."""
    def __init__(self):
        self.chatbots: Dict[str, Dict[str, List[BaseMessage]]] = {}

    async def create_chatbot(self, session: str, language: str):
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
            "pdf_name": None,
            "columns_and_types": None
        }


    async def set_table(self, session: str, table_name: str):
        try:
            self.chatbots[session]["table_name"] = table_name
            self.chatbots[session]["columns_and_types"] =  ",".join(f"{col}({dtype})" for col, dtype in get_all_columns_and_types(table_name))
        
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
        print(f"Getting chatbot for session: {session_id}: ", self.chatbots)
        if session_id not in self.chatbots:
            raise ValueError(f"No chatbot found for session '{session_id}'.")
        return self.chatbots[session_id]
    

    async def get_chatbot_table_name(self, session_id: str):
        if "table_name" not in self.chatbots[session_id]:
            return None
        return self.chatbots[session_id]["table_name"]
        

    async def get_chatbot_pdf_name(self, session_id: str):
        if "pdf_name" not in self.chatbots[session_id]:
            return None
        return self.chatbots[session_id]["pdf_name"]
    

    async def get_chatbot_columns_and_types(self, session_id: str):
        if "columns_and_types" not in self.chatbots[session_id]:
            return 
        return self.chatbots[session_id]["columns_and_types"]
    

    async def get_chatbot_config(self, session_id: str):
        if "config" not in self.chatbots[session_id]:
            return None  
        return self.chatbots[session_id]["config"]
    
    
    async def get_table_config(self, session_id: str, table_name: str):
        if table_name not in self.chatbots[session_id]["messages"]:
            return None
        return self.chatbots[session_id]["messages"][table_name]
    

    async def get_pdf_config(self, session_id: str, pdf_name: str):
        if pdf_name not in self.chatbots[session_id]["messages"]:
            return None
        return self.chatbots[session_id]["messages"][pdf_name]
    
    
    async def get_combo_config(self, session_id: str, table_name: str, pdf_name: str):
        if table_name not in self.chatbots[session_id]["messages"] or pdf_name not in self.chatbots[session_id]["messages"]:
            return None
        return self.chatbots[session_id]["messages"][table_name]


async def start_chatbot(session: str, manager):
    if session not in manager.chatbots:
        await manager.create_chatbot(session, "English")


async def set_table(session: str, table_name: str, manager):
    await manager.set_table(session, table_name)


async def set_pdf(session: str, pdf_name: str, manager):
    await manager.set_pdf(session, pdf_name)