from models.models import MessageInstance
from langchain_core.messages import HumanMessage
from llm_core.src.llm_utils.utility_function import *


async def set_chat_state(manager, session_id, message: MessageInstance):
    state = {
        "current_agent": None,
        "next_agent": None,
        "question": HumanMessage(content=message.message),
        "augmented_question": None,
        "answer": None,
        "table_name": await manager.get_chatbot_table_name(session_id),
        "table_relevant_data": None,
        "pdf_name": await manager.get_chatbot_pdf_name(session_id),
        "pdf_relevant_data": None,
        "messages": [HumanMessage(content=message.message)],
        "agent_scratchpads": [],
        "columns_and_types": await manager.get_chatbot_columns_and_types(session_id),
        "query_type": None,
        "answer_retrieval_query": None,
        "visualize_retrieval_query": None,
        "visualize_retrieval_label": None,
        "perform_manipulation_query": None,
        "perform_manipulation_label": None,
        "has_function_call": None,
        "function_call": None,
        "is_multiagent": False,
        "agent_step": 0,
        "runtime_queries": "",
        "query_failed": None,
        "message_number": 0
    }

    return state


