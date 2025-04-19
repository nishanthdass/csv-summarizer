from typing import Dict, cast
from fastapi import Request
from llm_core.services.chatbot_manager import ChatbotManager


def get_chatbot_manager(request: Request) -> ChatbotManager:
    """Returns the chatbot manager for the current user from the request."""
    user_id = request.session.get("user_data", {}).get("name")
    if not user_id:
        raise ValueError("No user ID in session.")

    if not hasattr(request.app.state, "managers"):
        request.app.state.managers = {}

    registry = request.app.state.managers
    
    if user_id not in registry:
        registry[user_id] = ChatbotManager()
    
    return registry[user_id]