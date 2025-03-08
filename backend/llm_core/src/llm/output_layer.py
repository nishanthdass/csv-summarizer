import asyncio
from models.models import MessageInstance
from langchain_core.messages import HumanMessage
from llm_core.src.utils.utility_function import *


async def start_next_agent_stream(manager, session_id, message_str: str, next_agent: str, time: float, thread_id: str):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
                    "event": "on_chain_start",
                    "message": message_str,
                    "table_name": await manager.get_chatbot_table_name(session_id),
                    "pdf_name": await manager.get_chatbot_pdf_name(session_id),
                    "role": next_agent,
                    "time": float_time,
                    "thread_id": thread_id
                }
    
    return message


async def char_agent_stream(manager, session_id, word_buffer: str, role: str, time: float):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
            "event": "on_chat_model_stream", 
            "message": word_buffer,
            "table_name": await manager.get_chatbot_table_name(session_id),
            "pdf_name": await manager.get_chatbot_pdf_name(session_id),
            "role": role,
            "time": float_time,
            }

    return message

async def usage_agent_stream(manager, session_id, usage_metadata: list, role: str, time: float):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
            "event": "on_chat_model_end", 
            "table_name": await manager.get_chatbot_table_name(session_id),
            "pdf_name": await manager.get_chatbot_pdf_name(session_id),
            "input_tokens": usage_metadata[0],
            "output_tokens": usage_metadata[1],
            "total_tokens": usage_metadata[2],
            "run_id": usage_metadata[3],
            "model_name": usage_metadata[5],
            "tool_call_name": usage_metadata[4],
            "role": role,
            "time": float_time,
            }

    return message

async def end_agent_stream(manager, session_id, message_str: str, role: str, time: float, visualizing_query: str, viewing_query_label: str):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
            "event": "on_chain_end", 
            "message": message_str,
            "table_name": await manager.get_chatbot_table_name(session_id),
            "pdf_name": await manager.get_chatbot_pdf_name(session_id),
            "role": role,
            "time": float_time,
            "visualizing_query": visualizing_query,
            "viewing_query_label": viewing_query_label
            }

    return message

async def query_agent_stream(manager, session_id, message_str: str, role: str, time: float, visualizing_query: str, viewing_query_label: str):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
            "event": "on_query_stream", 
            "message": message_str,
            "table_name": await manager.get_chatbot_table_name(session_id),
            "pdf_name": await manager.get_chatbot_pdf_name(session_id),
            "role": role,
            "time": float_time,
            "visualizing_query": visualizing_query,
            "viewing_query_label": viewing_query_label
            }

    return message

async def send_usage_message(manager, session_id, message_str: str, role: str, time: float):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
            "event": "on_usage_stream", 
            "message": message_str,
            "table_name": await manager.get_chatbot_table_name(session_id),
            "pdf_name": await manager.get_chatbot_pdf_name(session_id),
            "role": role,
            }

    return message

