import getpass
import os
from typing import Sequence, Dict, List, Literal
from typing_extensions import Annotated, TypedDict
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, trim_messages
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
import uuid
import asyncio

# Load environment variables
load_dotenv()

# Database and model setup
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST')
DB_PORT = os.getenv('POSTGRES_PORT')

os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_API_KEY"] = getpass.getpass()


db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Define state schema
class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    language: str
    next: str
    table_name: str  # Add this line


model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)


# Define trimmer for messages
trimmer = trim_messages(
    max_tokens=6500,
    strategy="last",
    token_counter=model,
    include_system=True,
    allow_partial=False,
    start_on="human",
)

# --- Define Node Functions ---

async def supervisor_node(state: State) -> State:
    # Trim messages as before
    trimmed_messages = trimmer.invoke(state["messages"])

    if trimmed_messages[-1].type == "ai":
        # Summarizing data scenario
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
            "You are a Writer that summarizes data from table {table_name} in a user-friendly manner and provides insights.\n\n"
            "Here is the data to summarize:\n{ai_message}")
        ]).invoke({"ai_message": trimmed_messages[-1].content if trimmed_messages else "",
                "table_name": state["table_name"]})
    else:
        # Deciding whether to use the DB or respond directly
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
            "You are the supervisor of a conversation about {table_name} table. Always consider the size of the table and the complexity of the question. Never make assumptions. Your tasks are:\n\n"
            "1. Analyze the user's request and assess if a few database queries are needed or if a deeper analysis is needed.\n\n"
            "If a few database queries are needed, respond ONLY with the exact text 'USE_DB'. This will trigger agent_1 to query the database.\n\n"
            "If the question requires a deeper analysis, such as large amounts of data and complex analysis, let the users know about the specific analysis needed.\n\n"
            "2. If you determine that no database query is needed or no deeper analysis is needed, respond directly and helpfully to the user.\n\n"
            "3. If the question has nothing to do with the {table_name} table, decline to help the user.\n\n"
            "The user's last request:\n{user_message}")
        ]).invoke({"user_message": trimmed_messages[-1].content if trimmed_messages else "",
                "table_name": state["table_name"]})

    response = await model.ainvoke(prompt)
    print(response)
    decision_text = response.content

    if decision_text == "USE_DB":
        # Decide to use agent_1 for database lookup
        return {"messages": [response], "next": "agent_1"}
    else:
        return {"messages": [response], "next": "__end__"}


async def agent_1_node(state: State) -> State:
    user_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    # Access the table_name from state
    table_name = state["table_name"]

    # Retrieve the sql_agent for this table from manager
    global manager
    sql_agent_for_table = manager.chatbots[table_name]["sql_agent"]
    sql_result = sql_agent_for_table.run(user_message)

    result_message = AIMessage(content=sql_result)
    return {"messages": [result_message], "next": "supervisor"}

# --- Build the State Graph ---
workflow = StateGraph(state_schema=State)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("agent_1", agent_1_node)
# Later: workflow.add_node("agent_2", agent_2_node)

# Start from supervisor
workflow.add_edge(START, "supervisor")
# workflow.add_conditional_edges("supervisor", lambda s: s["next"])
workflow.add_edge("agent_1", "supervisor")
workflow.add_conditional_edges("supervisor", lambda s: "agent_1" if s["next"] == "agent_1"  else "__end__")

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# The rest of your ChatbotManager and main logic remain the same:
class ChatbotManager:
    def __init__(self):
        self.chatbots: Dict[str, Dict[str, List[BaseMessage]]] = {}

    async def create_chatbot(self, table_name: str, language: str):
        if table_name in self.chatbots:
            raise ValueError(f"Chatbot for table '{table_name}' already exists.")
        
        # Create a table-specific db object
        db_for_table = SQLDatabase.from_uri(db_url, include_tables=[table_name])
        sql_agent_for_table = create_sql_agent(llm=model, db=db_for_table, agent_type="openai-tools", verbose=True)

        new_uuid = uuid.uuid4()
        config = {"configurable": {"thread_id": f"{table_name}_{new_uuid}"}}
        self.chatbots[table_name] = {
            "language": language,
            "messages": [],
            "config": config,
            "sql_agent": sql_agent_for_table,  # store the table-specific agent
            "table_name": table_name
        }
        print(f"Chatbot for table '{table_name}' initialized.")


    async def add_chatbot_message(self, table_name: str, message: BaseMessage):
        if table_name not in self.chatbots:
            raise ValueError(f"No chatbot found for table '{table_name}'.")
        self.chatbots[table_name]["messages"].append(message)

    async def get_messages(self, table_name: str) -> List[BaseMessage]:
        if table_name not in self.chatbots:
            raise ValueError(f"No chatbot found for table '{table_name}'.")
        return self.chatbots[table_name]["messages"]

    async def call_model_for_table(self, table_name: str):
        if table_name not in self.chatbots:
            raise ValueError(f"No chatbot found for table '{table_name}'.")
        
        state = {
            "messages": await self.get_messages(table_name),
            "language": self.chatbots[table_name]["language"],
            "next": "supervisor",
            "table_name": table_name,
        }
        config = self.chatbots[table_name]["config"]
        response = await app.ainvoke(state, config)
        # The last message in the response should be the new AI message from agent_1
        if "messages" in response:
            await self.add_message(table_name, response["messages"][-1])
        return response
    
    async def stream_for_table(self, table_name: str):
        if table_name not in self.chatbots:
            raise ValueError(f"No chatbot found for table '{table_name}'.")

        state = {
            "messages": await self.get_messages(table_name),
            "language": self.chatbots[table_name]["language"],
            "next": "supervisor",
            "table_name": table_name
        }
        config = self.chatbots[table_name]["config"]

        async for chunk, metadata in app.astream(state, config, stream_mode="messages"):
            if isinstance(chunk, AIMessage):
                yield chunk
    
    async def stream_events_for_table(self, table_name: str):
        if table_name not in self.chatbots:
            raise ValueError(f"No chatbot found for table '{table_name}'.")

        state = {
            "messages": await self.get_messages(table_name),
            "language": self.chatbots[table_name]["language"],
            "next": "supervisor",
            "table_name": table_name
        }
        config = self.chatbots[table_name]["config"]

        async for event in app.astream_events(state, config, version="v2"):
            yield event

manager = ChatbotManager()

# Example usage with streaming
async def main():
    await manager.create_chatbot("housing", "English")
    # await manager.add_message("housing", HumanMessage(content="Hello!"))

    # async for event in manager.stream_events_for_table("housing"):
    #     if event["event"] == "on_chat_model_stream":
    #         print(event["data"])
    #     if event["event"] == "on_chat_model_end":
    #         await manager.add_message("housing", event["data"]["output"])

    await manager.add_chatbot_message("housing", HumanMessage(content="How many homes are there in the table?"))
    async for event in manager.stream_events_for_table("housing"):
        if event["event"] == "on_chat_model_end":
            print(event["data"]["output"])
            pass
        # Check if the final state indicates the workflow ended
            # if event["data"]["next"] == "__end__":
            #     print(event["data"])
            #     break
        # if event["event"] == "on_chat_model_end":
        #     # print(event["data"]["output"])
        #     pass
        # if event["event"] == "on_chat_model_stream":
        #     print(event["data"])
        # if event["event"] == "on_chat_model_end":
        #     await manager.add_message("housing", event["data"]["output"])
    
    # messages = await manager.get_messages("housing")
    # print(messages)


if __name__ == "__main__":
    asyncio.run(main())
