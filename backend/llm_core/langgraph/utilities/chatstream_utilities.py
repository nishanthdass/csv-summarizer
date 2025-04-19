from llm_core.services.chatbot_manager import ChatbotManager
from llm_core.langgraph.models.models import MessageInstance
from langchain_core.messages import HumanMessage


async def set_chat_state(chatbot, session_id, message: MessageInstance):
    """Initialize the chat state based on message and session context."""
    state = {
        "current_agent": None,
        "next_agent": None,
        "question": HumanMessage(content=message.message),
        "augmented_question": None,
        "answer": None,
        "table_name": message.table_name,
        "table_relevant_data": None,
        "pdf_name": message.pdf_name,
        "pdf_relevant_data": None,
        "messages": [HumanMessage(content=message.message)],
        "agent_scratchpads": [],
        "query_type": message.query_type,
        "answer_retrieval_query": message.answer_retrieval_query,
        "visualize_retrieval_query": message.visualizing_query,
        "visualize_retrieval_label": message.viewing_query_label,
        "perform_manipulation_query": None,
        "perform_manipulation_label": None,
        "has_function_call": message.has_function_call,
        "function_call": message.tool_call_name,
        "is_multiagent": False,
        "agent_step": 0,
        "runtime_queries": "",
        "query_failed": None,
    }
    return state