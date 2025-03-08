from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, AIMessageChunk
from typing import Dict, List
from db.db_utility import get_all_columns_and_types
import uuid
from rich import print as rprint

class ChatbotManager:
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
            "messages": [],
            "config": config,
            "table_name": None,
            "pdf_name": None,
            "columns_and_types": None
        }


    async def alter_table_name(self, session: str, table_name: str):
        try:
            rprint("Table name: ", table_name)
            rprint("Session: ", session)
            rprint("Chatbot session: ",  self.chatbots[session])
            self.chatbots[session]["table_name"] = table_name
            rprint("Table name set for session: ", session)
            self.chatbots[session]["columns_and_types"] = get_all_columns_and_types(table_name)
            rprint("Columns and types set for session: ", session)
        
        except Exception as e:
            raise RuntimeError(f"Failed to add or replace Table name for session {session}: {e}")
        

    async def alter_pdf_name(self, session: str, pdf_name: str):
        try:
            self.chatbots[session]["pdf_name"] = pdf_name
        
        except Exception as e:
            raise RuntimeError(f"Failed to add or replace PDF name for session {session}: {e}")


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
    

async def start_chatbot(session: str, manager):
    await manager.create_chatbot(session, "English")


async def alter_table_name(session: str, table_name: str, manager):
    await manager.alter_table_name(session, table_name)
    if await manager.get_chatbot_table_name(session) is not None and await manager.get_chatbot_pdf_name(session) is not None:
        rprint("Both table name and pdf name are set for session: ", session)
        
    else:
        rprint("Either table name or pdf name is not set for session: ", session)


async def alter_pdf_name(session: str, pdf_name: str, manager):
    await manager.alter_pdf_name(session, pdf_name)
    if await manager.get_chatbot_table_name(session) is not None and await manager.get_chatbot_pdf_name(session) is not None:
        rprint("Both table name and pdf name are set for session: ", session)
    else:
        rprint("Either table name or pdf name is not set for session: ", session)