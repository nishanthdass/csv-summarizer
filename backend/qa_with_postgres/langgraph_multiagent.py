import os
import uuid
import asyncio
import random
import json
import emoji
from typing import Sequence, Dict, List, Optional
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
from langchain_core.messages import  trim_messages
from langchain_core.tools import tool
from langchain_core.output_parsers import JsonOutputParser, BaseOutputParser
from pydantic import BaseModel, Field
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.agents.format_scratchpad.openai_tools import (format_to_openai_tool_messages)
from langgraph.types import interrupt, Command
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
from langchain_core.runnables import RunnableConfig

load_dotenv()

list_user_messages = ["I need to be able to predict the cost of housing based on the prices in the table",

"I am looking to make investment decisions for my business. I will need to take the predicted prices from the model and use it in my business",

"I want to use Root Mean Squared Error (RMSE)", 

"What do you mean by assumptions? give me an example",

"We are on the right track, We are not making any assumptions!",

"How many homes are there in the table?"]


# Database and model setup
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST')
DB_PORT = os.getenv('POSTGRES_PORT')
db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
collection_name = "step_1_ML_project_checklist"

# Set up tracing for debugging
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Initialize model and embedding model
model = ChatOpenAI(model="gpt-4o", temperature=0)
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

# Initialize vector store and retriever
vector_store = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=db_url,
    use_jsonb=True,
)
retriever = vector_store.as_retriever(search_kwargs={"k": 3})


# Define schemas and tools

@tool
async def retreive_pgvector(query: str) -> int:
    """Retrieves the pgvector for a given query."""
    return await retriever.invoke(query)

# Define trimmer for message storage
trimmer = trim_messages(
    max_tokens=6500,
    strategy="last",
    token_counter=model,
    include_system=True,
    allow_partial=False,
    start_on="human",
)


class MessageState(TypedDict):
    """Schema for state."""
    current_agent: str
    next_agent: str
    question: str
    answer: str
    table_name: str  # Add this line
    messages: Annotated[Sequence[BaseMessage], add_messages]
    agent_scratchpads: list



class Route(BaseModel):
    """Schema for routing a question to an agent."""
    current_agent: str = Field(description="name of the current agent")
    next_agent: str = Field(description="name of the agent to route the question to")
    question: str = Field(description="question to route to the agent")
    answer: Optional[str] = Field(default=None, description="answer to the question, if answer is not ready yet then None")
    competed_step: Optional[int] = Field(default=None, description="step that the agent has completed")


def find_word(word, word_to_build, string_builder):
    string_builder += word
    if string_builder != word_to_build[:len(string_builder)]:
        string_builder = ''
    else:
        if string_builder == word_to_build:
            return string_builder
        return string_builder

# --- Define Node Functions ---
async def supervisor_node(state: MessageState) -> MessageState:
    """Supervisor Node to route questions to agents."""
    print(f"Supervisor Node 🤖")
    state["current_agent"] = "supervisor"
    if state["next_agent"] != "supervisor":
        return {"messages": state["messages"], "next": state["next"]}

    conversation_history = state["messages"]
    trimmed_messages = trimmer.invoke(state["messages"])

    parser = JsonOutputParser(pydantic_object=Route)
    prompt = ChatPromptTemplate.from_messages([
        ("system", 
        "You are the supervisor of a conversation about a table that goes by {table_name}. Never make assumptions about the content of the table based on the name of the table as a bananas column can exist in the table. Ensure that all decisions are based on facts from queries or from the other agents."
        "Your tasks are:\n\n"
        "1. If a few database queries are needed to answer the user's question, then route the question to `sql_agent`. DO not make assumptions.\n\n"
        "2. If the question requires predictive analysis route it to `data_analyst`.\n\n"
        "3. If no database query or deeper analysis is needed, set the next_agent to '__end__' and answer the question.\n\n"
        "4. If nessecary, look through {conversation_history} to look at previous messages for context.\n\n"
        "5. If the question has nothing to do with the {table_name} table, set the next_agent to '__end__' and explain why. Never assueme anything about the table"
        "the question is unrelated.\n\n"
        "Return in json format:\n"
        "{{\"current_agent\": \"supervisor\", \"next_agent\": \"agent_name\", \"question\": \"question_text\", \"answer\": \"<_START_> answer_text <_END_>\"}}\n\n"
        "The user's last request:\n{user_message}")
    ])

    chain = prompt | model | parser

    inputs = {
        "user_message": trimmed_messages[-1].content if trimmed_messages else "",
        "table_name": state["table_name"],
        "conversation_history": conversation_history
    }

    response = await chain.ainvoke(inputs)

    state["messages"].append(AIMessage(content=response["answer"]))
    state["answer"] = AIMessage(content=response["answer"])
    state["next_agent"] = response["next_agent"]

    if response["next_agent"] == "supervisor":
        state['next_agent'] = "__end__"
        return state

    if response["next_agent"] == "sql_agent" or response["next_agent"] == "data_analyst":
        return state


async def sql_agent_node(state: MessageState) -> MessageState:
    """SQL Agent Node (SQL Agent Node -> SQL Validator -> __end__)"""
    print(f"SQL Agent Node 👾")
    state["current_agent"] = "sql_agent"

    user_message = state["question"]

    table_name = state["table_name"]
    global manager
    sql_agent_for_table = manager.chatbots[table_name]["sql_agent"]
    sql_result = sql_agent_for_table.invoke(user_message)

    # Include intermediate steps in the agent scratchpad
    intermediate_steps = sql_result.get("intermediate_steps", [])
    intermediate_steps =format_to_openai_tool_messages(intermediate_steps)
    result_message = AIMessage(content=sql_result["output"])
    state["answer"] = result_message
    state["messages"].append(result_message)
    state["agent_scratchpads"].append(intermediate_steps)
    state["next_agent"] = "sql_validator"

    return state

async def sql_validator_node(state: MessageState) -> MessageState:
    """SQL Validator Node (SQL Agent Node -> SQL Validator -> __end__)"""
    print("SQL Validator Node 👾")
    state["current_agent"] = "sql_validator"

    user_message = state["question"].content
    ai_message = state["answer"].content
    agent_scratchpad = state["agent_scratchpads"][-1]

    parser = JsonOutputParser(pydantic_object=Route)
    
    prompt = ChatPromptTemplate.from_messages([
            ("system",
            "Return in json format:\n"
            "{{\"current_agent\": \"sql_validator\", \"next_agent\": \"__end__\", \"question\": \"question_text\", \"answer\": \"<_START_> answer_text <_END_>\"}}\n\n"
            "You are a data analysist with expertise in understanting data. Your task is to validate the answer to the user's question.\n\n"
            "The user's last request:\n{user_message}\n\n"
            "Here is the message from the agent:\n{ai_message}. \n\n"
            "Look at the agent scratchpad: {agent_scratchpad}. \n\n"
            "Ensure the answer is correct and informative based on the agent's question and the queries in the agent scratchpad. If the answer is correct, then simply return the message {ai_message}. If the answer is not specific enough, and requires a more indepth analyis, then let the user know. \n\n")
        ])
    
    # print("agent_scratchpad", state["agent_scratchpads"])
    inputs = { "ai_message": ai_message,
                "agent_scratchpad": agent_scratchpad,
                "user_message": user_message}



    chain = prompt | model | parser

    response = await chain.ainvoke(inputs)
    
    state["messages"].append(AIMessage(content=response["answer"]))
    state["answer"] = AIMessage(content=response["answer"])
    state["next_agent"] = response["next_agent"]

    return state



async def data_analyst_node(state: MessageState) -> MessageState:
    """Data Analyst Node ((Data Analyst Node <->  Human Input) -> Cleanup -> __end__)"""
    print("Data Analyst Node 👾")
    trimmed_messages = trimmer.invoke(state["messages"])
    
    parser = JsonOutputParser(pydantic_object=Route)

    prompt = ChatPromptTemplate.from_messages([
            ("system", 
            "You are a data analysis agent with expertise in hands on Machine Learning processes with a specializtion in supervised learning. Do not exit the loop until after step 4 and do not repeat completed steps.\n\n"
            "Always respond in json format and make sure to mark a step as completed in the completed_step field after evaluating a response:\n"
            "{{\"current_agent\": \"data_analyst\",\"next_agent\": \"human_input or __end__\", \"question\": \"<_START_> question_text <_END_>\", \"answer\": \" <_START_> response to step 4 <_END_> \", \"completed_step\": \"completed steps\"}}\n\n"
            "Step 1 is to ask the user to confirm how they expect to use and benefit from the suggested model.\n\n"
            "Wait on users response to Step 1 before moving on.\n\n"
            "Step 2 is to select a Performance Measure based on the user's answer to Step 1. Our options are Regression Metrics (Mean Absolute Error, Mean Squared Error, Root Mean Squared Error, Root Mean Squared Log Error, R Squared, Adjusted R Squared) or Classification Metrics (Precision, Accuracy, Recall, F1).\n\n"
            "Wait on users response to Step 2 before moving on.\n\n"
            "Step 3 is to check the assumptions the user may be making. Catch assumptions such as misinterpreting a regression problem for a classification one.\n\n"
            "Wait on users response to Step 3 before moving on.\n\n"
            "Step 4 is to provide a summary of the responses from Step 1, 2, and 3. Insert the summary into the answer field and set the next_agent field to '__end__'.\n\n"
            "The conversation so far:\n{user_message}\n\n")
        ])

    inputs = {
        "user_message": trimmed_messages,
        "table_name": state["table_name"]
    }

    chain = prompt | model | parser
    parsed_result = await chain.ainvoke(inputs)
    print("processed")
    print("parsed_result: ", parsed_result)

    if parsed_result["question"] != "":
        state["messages"].append(AIMessage(content=f"{parsed_result["question"]}"))
    state["answer"] = AIMessage(content=f"{parsed_result['answer']}")

    # print("messages", state["messages"])

    if parsed_result["next_agent"] == "human_input":
        return Command(goto="human_input")
    else:
        print("END OF HUMAN IN THE LOOP")
        state["next_agent"] = parsed_result["next_agent"]
        state["messages"].append(AIMessage(content=f"{parsed_result['answer']}"))
        # print("state: ", state)
        return state

async def human_input(state: MessageState):
    """Human Input Node to get user input and communicate with Data Analyst"""
    print("Human Input Node 🤠")
    human_message = interrupt("human_input")

    print("human_message: ", human_message)

    return {
        "messages": [
            {
                "role": "human",
                "content": human_message
            }
        ],
        "next_agent": "data_analyst"
    }

async def cleanup_node(state: MessageState) -> MessageState:
    print("Cleanup Node 👾")
    return {"messages": [], "next_agent": "__end__"}

# --- Build the State Graph ---
workflow = StateGraph(state_schema=MessageState)

# Nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("sql_agent", sql_agent_node)
workflow.add_node("sql_validator", sql_validator_node)
workflow.add_node("data_analyst", data_analyst_node)
workflow.add_node("human_input", human_input)
workflow.add_node("cleanup", cleanup_node)
# Edges
workflow.add_edge(START, "supervisor")
workflow.add_edge("sql_agent", "sql_validator")
workflow.add_edge("sql_validator", END)

workflow.add_edge("data_analyst", END)
workflow.add_edge("human_input", "data_analyst")
# workflow.add_edge("cleanup", END)

workflow.add_conditional_edges("supervisor", lambda state: state["next_agent"])

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


class ChatbotManager:
    def __init__(self):
        self.chatbots: Dict[str, Dict[str, List[BaseMessage]]] = {}

    async def create_chatbot(self, table_name: str, language: str):
        if table_name in self.chatbots:
            raise ValueError(f"Chatbot for table '{table_name}' already exists.")

        db_for_table = SQLDatabase.from_uri(db_url, include_tables=[table_name])
        toolkit = SQLDatabaseToolkit(db=db_for_table, llm=model)
        tools = toolkit.get_tools()
        sql_agent_for_table = create_sql_agent(llm=model, toolkit=toolkit, agent_type="openai-tools", verbose=False, agent_executor_kwargs={"return_intermediate_steps": True})

        thread_uuid = uuid.uuid4()
        parent_run_uuid = uuid.uuid4()
        run_uuid = uuid.uuid4()
        config = {"configurable": {"thread_id": f"{thread_uuid}"}, "recursion_limit": 100}
        self.chatbots[table_name] = {
            "language": language,
            "messages": [],
            "config": config,
            "sql_agent": sql_agent_for_table,  # store the table-specific agent
            "table_name": table_name
        }
        print(f"Chatbot for table '{table_name}' initialized.")

    async def get_chatbot(self, table_name: str):
        if table_name not in self.chatbots:
            raise ValueError(f"No chatbot found for table '{table_name}'.")
        return self.chatbots[table_name]

    async def add_chatbot_message(self, table_name: str, message: BaseMessage):
        if table_name not in self.chatbots:
            raise ValueError(f"No chatbot found for table '{table_name}'.")

        self.chatbots[table_name]["messages"].append(message)

    async def get_messages(self, table_name: str) -> List[BaseMessage]:
        if table_name not in self.chatbots:
            raise ValueError(f"No chatbot found for table '{table_name}'.")
        return self.chatbots[table_name]["messages"]
    

manager = ChatbotManager()

def find_word_in_text( word, words_to_find, word_buffer):
    # print( "input word: ", word )
    for word_to_find in words_to_find:
        if word_to_find in word_buffer:
            return [True, word_to_find]
    return [False, None]

def update_word_state(find_word, words_to_find, word_buffer, word_state):
    """Update the word state based on the matched word."""
    if find_word in ["<_START_>", "```sql"]:
        return True, ""
    elif find_word in ["<_", "```"] and word_state and word_buffer:
        return False, word_buffer
    return word_state, word_buffer


def process_response(word, str_response, char_backlog):
    """Process the response string and handle backlog characters."""
    str_response.append(word)

    if len(str_response) == 1 and str_response[0] == ">":
        str_response.pop(0)

    if str_response and str_response[-1].strip() == "<":
        char_backlog.append(str_response.pop())
    else:
        if char_backlog:
            char_backlog.append(str_response.pop() if str_response else "")
        else:
            pass
            # print("".join(str_response)) 
    if len(char_backlog) > 1:
        char_backlog.clear()

    return str_response, char_backlog


def handle_finish_reason(event, word_state, char_backlog):
    """Handle the finish reason and reset states if needed."""
    if 'finish_reason' in event["data"]['chunk'].response_metadata:
        reason = event["data"]['chunk'].response_metadata['finish_reason']
        if reason == "stop":
            return False, []
    return word_state, char_backlog


def process_stream_event(event, words_to_find, word_buffer, word_state, str_response, char_backlog):
    """Process a single streaming event and update the state."""
    word = event["data"]['chunk'].content
    word_buffer += word

    find_word = find_word_in_text(word, words_to_find, word_buffer)

    # Update word state
    word_state, word_buffer = update_word_state(find_word[1], words_to_find, word_buffer, word_state)

    # Process response if in word state
    if word_state:
        str_response, char_backlog = process_response(word, str_response, char_backlog)
    else:
        str_response = []

    # Handle finish reason
    word_state, char_backlog = handle_finish_reason(event, word_state, char_backlog)

    return word_buffer, word_state, str_response, char_backlog


async def main():

    await manager.create_chatbot("housing", "English")
    chatbot = await manager.get_chatbot("housing")

    config = chatbot["config"]


    while True:
        
        message = input("Enter a message: ")

        state = {
            "current_agent": None,
            "next_agent": "supervisor",
            "question": HumanMessage(content=message),
            "answer": None,
            "table_name": "housing",
            "messages": [HumanMessage(content=message)],
            "agent_scratchpads": []
        }

        

        is_interrupted = False
        while_loop = True
        
        words_to_find = ['<_START_>', '```sql', '<_', '```']
        word_buffer = ""
        word_state = False
        str_response = []
        char_backlog = []

        context = {
        'word_buffer': "",
        'word_state': False,
        'str_response': [],
        'char_backlog': [],
        'words_to_find': ['<_START_>', '```sql', '<_', '```']
        }

        input_arg = state
        

        while while_loop:
            if is_interrupted:
                print("Interrupted: ", len(interrupts.tasks))
                message = input("Enter a message during interruption: ")
                input_arg = Command(resume=message)

            async for event in app.astream_events(input_arg, config, version="v2"):
                if event["event"] == "on_chain_error":
                    print("Error: ", event["data"])
                if event["event"] == "on_chat_model_stream":
                    word_buffer, word_state, str_response, char_backlog = process_stream_event(
                        event, words_to_find, word_buffer, word_state, str_response, char_backlog
                    )

                if event["event"] == "on_chain_end" and not is_interrupted:
                    if "output" in event['data']:
                        if type(event['data']['output']) == dict and 'next_agent' in event['data']['output']:
                            if event['data']['output']['next_agent'] == "__end__":
                                while_loop = False
                                break

                interrupts = app.get_state(config)
                if len(interrupts.tasks) > 0 and interrupts.tasks[0].interrupts and not is_interrupted:
                    print("Event: Interrupted: ", interrupts.tasks[0].interrupts)
                    is_interrupted = True
                    break
                elif len(interrupts.tasks) == 0 and is_interrupted:
                    is_interrupted = False
        


            # if not is_interrupted:
            #     # print("Not Interrupted: ")
            #     async for event in app.astream_events(state, config, version="v2"):
            #         if event["event"] == "on_chat_model_stream":
            #             word_buffer, word_state, str_response, char_backlog = process_stream_event(
            #                 event, words_to_find, word_buffer, word_state, str_response, char_backlog
            #             )

            #         if event["event"] == "on_chain_end":
            #             if "output" in event['data']:
            #                 if type(event['data']['output']) == dict and 'next_agent' in event['data']['output']:
            #                     if event['data']['output']['next_agent'] == "__end__":
            #                         while_loop = False
            #                         break

            #         interrupts = app.get_state(config)
            #         if len(interrupts.tasks) > 0 and interrupts.tasks[0].interrupts:
            #             is_interrupted = True
            #             # print("Event: Interrupted: ", event)
            #             break


            # if is_interrupted:
            #     # print("Interrupted: ")
            #     message = input("Enter a message during interruption: ")
            #     interrupts = app.get_state(config)
            #     is_interrupted = False
            #     # await app.ainvoke(Command(resume=message), config)
            #     async for event in app.astream_events(Command(resume=message), config, version="v2"):
            #         if event["event"] == "on_chat_model_stream":
            #             word_buffer, word_state, str_response, char_backlog = process_stream_event(
            #                 event, words_to_find, word_buffer, word_state, str_response, char_backlog
            #             )

    
if __name__ == "__main__":
    asyncio.run(main())
