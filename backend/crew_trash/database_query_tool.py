from typing import Type, ClassVar
from crewai_tools import BaseTool
from pydantic import BaseModel, Field
from qa_with_postgres.chatbot import ChatBot

class ChatBotToolInput(BaseModel):
    """Input schema for ChatBotTool."""
    question: str = Field(..., description="The agent's question for querying the database.")
    table_name: str = Field(..., description="The name of the table to query in the database.")

class ChatBotTool(BaseTool):
    name: str = "Database Query Tool"
    description: str = "Queries the database to answer user questions using ChatBot."
    args_schema: Type[BaseModel] = ChatBotToolInput
    
    

    def _run(self, question: str, table_name: str) -> str:
        """
        Executes the tool's logic using ChatBot to answer a question.

        Args:
            question (str): The agent's question for querying the database.
            table_name (str): The target table name for the query.
        
        Returns:
            str: The response from ChatBot.
        """
        # Use the ChatBot instance to get the response
        chatbot = ChatBot(table_name=table_name)
        
        response = chatbot.get_response(question=question, table_name=table_name)
        return response