import asyncio
from models.models import MessageInstance
from langchain_core.messages import HumanMessage
from llm_core.src.utils.utility_function import *

message_queue = asyncio.Queue()


state = {
                "current_agent": None,
                "next_agent": None,
                "question": None,
                "answer": None,
                "table_name": None,
                "pdf_name": None,
                "messages": None,
                "agent_scratchpads": [],
                "columns_and_types": None,
                "answer_query": None,
                "viewing_query_label": None,
                "has_function_call": None,
                "function_call": None
            }


async def start_chat_state(manager, session_id, message: MessageInstance):
    state = {
        "current_agent": None,
        "next_agent": "supervisor",
        "question": HumanMessage(content=message.message),
        "answer": None,
        "table_name": await manager.get_chatbot_table_name(session_id),
        "pdf_name": await manager.get_chatbot_pdf_name(session_id),
        "messages": [HumanMessage(content=message.message)],
        "agent_scratchpads": [],
        "columns_and_types": await manager.get_chatbot_columns_and_types(session_id),
        "answer_query": None,
        "viewing_query_label": None,
        "has_function_call": None,
        "function_call": None
    }

    return state

