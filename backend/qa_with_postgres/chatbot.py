# ChatBot.py
import os
from typing import List, Tuple
from qa_with_postgres.load_config import LoadConfig
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
from sqlalchemy import create_engine
from langchain_community.agent_toolkits import create_sql_agent
import langchain
langchain.debug = True

APPCFG = LoadConfig()

class ChatBot:
    """
    A ChatBot class capable of responding to messages.
    It interacts with SQL databases and leverages LangChain agents for Q&A.
    """

    def __init__(self):
        # Initialize components once during instantiation
        self.db = SQLDatabase.from_uri(APPCFG.connection_string)
        self.execute_query = QuerySQLDataBaseTool(db=self.db)
        self.write_query = create_sql_query_chain(APPCFG.langchain_llm, self.db)
        self.answer_prompt = PromptTemplate.from_template(APPCFG.agent_llm_system_role)
        self.answer = self.answer_prompt | APPCFG.langchain_llm | StrOutputParser()
        self.chain = (
            RunnablePassthrough.assign(query=self.write_query).assign(
                result=itemgetter("query") | self.execute_query
            )
            | self.answer
        )

    def respond(self, chatbot: List, message: str) -> Tuple:
        """
        Respond to a message without using conversation history.

        Args:
            chatbot (List): A list representing the chatbot's conversation history.
            message (str): The user's input message to the chatbot.

        Returns:
            Tuple[str, List]: An empty string (placeholder) and the updated chatbot conversation list.
        """
        # Invoke the chain with the current message
        response = self.chain.invoke({"question": message})
        chatbot.append((message, response))
        return "", chatbot
