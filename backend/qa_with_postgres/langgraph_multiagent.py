import os
import uuid
import asyncio
import math
from fastapi import WebSocket
from typing import Sequence, Dict, List, Optional
from typing_extensions import Annotated, TypedDict
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, AIMessageChunk
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import  trim_messages
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.agents.format_scratchpad.openai_tools import (format_to_openai_tool_messages)
from langgraph.types import interrupt, Command
import logging
from rich import print as rprint
from qa_with_postgres.load_config import LoadOpenAIConfig, LoadPostgresConfig
from langchain.chains import RetrievalQAWithSourcesChain
from qa_with_postgres.kg_retrieval import kg_retrieval_window
from langchain_core.prompts import PromptTemplate
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.callbacks.manager import AsyncCallbackManager
import time# Start timer


# Set up tracing for debugging
os.environ["LANGCHAIN_TRACING_V2"] = "true"


openai_var  = LoadOpenAIConfig()
postgres_var = LoadPostgresConfig()
model = ChatOpenAI(model="gpt-4o", temperature=0)
db = LoadPostgresConfig()

time_table = { "supervisor": 0, "pdf_agent": 0, "pdf_validator": 0, "call_sql_agent": 0, "sql_agent": 0, "sql_validator": 0, "data_analyst": 0, "human_input": 0, "cleanup": 0}

tasks = {}
active_websockets = {}
active_chatbots = {}

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
    table_name: str
    pdf_name: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    agent_scratchpads: list
    columns_and_types: str
    modified_query: str
    modified_query_label: str




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

def get_all_columns_and_types(table_name, db):

    columns_and_types = []
    conn = db.get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}';")
    columns_and_types = cur.fetchall()

    cur.close()
    conn.close()

    response = ""
    for i in range(len(columns_and_types)):
        column_name, postgres_type = columns_and_types[i]
        response +=  str(column_name) + "(" + str(postgres_type) + ") + ,"

    return response

# --- Define Node Functions ---
async def supervisor_node(state: MessageState) -> MessageState:
    """Supervisor Node to route questions to agents."""
    time_table["supervisor"] = time.time()
    state["current_agent"] = "supervisor"
    if state["next_agent"] != "supervisor":
        return {"messages": state["messages"], "next": state["next"]}

    conversation_history = state["messages"]
    trimmed_messages = trimmer.invoke(state["messages"])

    parser = JsonOutputParser(pydantic_object=Route)

    if state["table_name"] is None and state["pdf_name"] is None:
        prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are the supervisor of a conversation about the data in csv tables and pdf documentations.\n\n"
            "The user has  not selected a table or pdf yet. Never make assumptions about the content of the table or pdf.\n\n"
            "Simply let the user know that you do not have access to the tables or pdfs and ask them to select a table and/or pdf.\n\n"
            "Return in json format and set the next agent to '__end__:\n"
            "{{\"current_agent\": \"supervisor\", \"next_agent\": \"agent_name\", \"question\": \"question_text\", \"answer\": \"<_START_> answer_text <_END_>\"}}\n\n"
            "The user's last request:\n{user_message}")
        ])

    elif state["table_name"] is None and state["pdf_name"] is not None:
        prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are the supervisor of a conversation about a pdf document that goes by {pdf_name}.\n\n" 
            "Never make assumptions about the content of the pdf.\n\n"
            "Simply let the user know that you can route the question to `pdf_agent` who can answer the question.\n\n"
            "Return in json format and set the next_agent to 'pdf_agent':\n"
            "{{\"current_agent\": \"supervisor\", \"next_agent\": \"agent_name\", \"question\": \"question_text\", \"answer\": \"<_START_> answer_text <_END_>\"}}\n\n"
            "The user's last request:\n{user_message}" )
        ])

    elif state["table_name"] is not None and state["pdf_name"] is None:
        prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are the supervisor of a conversation about a table that goes by {table_name}. Never make assumptions about the content of the table based on the name of the table as a bananas column can exist in the table. Ensure that all decisions are based on facts from queries or from the other agents."
            "Your tasks are:\n\n"
            "1. If a few database queries are needed to answer the user's question, then route the question to `sql_agent`. DO not make assumptions.\n\n"
            "2. If the question requires predictive analysis route it to `data_analyst`.\n\n"
            "3. If no database query or deeper analysis is needed, set the next_agent to '__end__' and answer the question.\n\n"
            "4. If nessecary, look through {conversation_history} to look at previous messages for context.\n\n"
            "5. If the question has nothing to do with the {table_name} or if {table_name} is None table, set the next_agent to '__end__' and explain why. Never assueme anything about the table"
            "the question is unrelated.\n\n"
            "Return in json format:\n"
            "{{\"current_agent\": \"supervisor\", \"next_agent\": \"agent_name\", \"question\": \"question_text\", \"answer\": \"<_START_> answer to question or the step being taken to answer the question <_END_>\", \"modified_query\": The previously created sql_agent query(with the ctid) or an empty string. Only use when retrieving answer from conversation_history.\", \"modified_query_label\": The previously created sql_agent query(with the label) or an empty string.\"}}\n\n"
            "The user's last request:\n{user_message}")
        ])

    elif state["table_name"] is not None and state["pdf_name"] is not None:
        prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are the supervisor of a conversation about a table that goes by {table_name} and a pdf that goes by {pdf_name}.\n\n"
            "Never make assumptions about the content of the table or pdf.\n\n"
            "Currently you are unable to provide services when the users has both a table and a pdf selected simultaneously.\n\n"
            "Simply let the user know that the feature to provide services for both table and pdf is not available yet and the user should select either a table or a pdf.\n\n"
            "Return in json format and set the next_agent to '__end__':\n"
            "{{\"current_agent\": \"supervisor\", \"next_agent\": \"agent_name\", \"question\": \"question_text\", \"answer\": \"<_START_> answer_text <_END_>\"}}\n\n"
            "The user's last request:\n{user_message}")
        ])
    

    chain = prompt | model | parser

    inputs = {
        "user_message": trimmed_messages[-1].content if trimmed_messages else "",
        "table_name": state["table_name"],
        "pdf_name": state["pdf_name"],
        "conversation_history": conversation_history
    }


    try:
        response = await chain.ainvoke(inputs)
    except Exception as e:
        logging.error(f"Error invoking chain: {e}")
        response = None

    state["messages"].append(AIMessage(content=response["answer"]))
    state["answer"] = AIMessage(content=response["answer"])
    state["next_agent"] = response["next_agent"]


    if response["next_agent"] == "supervisor":
        state['next_agent'] = "__end__"
        return state

    if response["next_agent"] == "sql_agent" or response["next_agent"] == "data_analyst" or response["next_agent"] == "pdf_agent":
        rprint("Supervisor time: ", time_table["supervisor"])
        return state
    

async def pdf_agent_node(state: MessageState) -> MessageState:
    """PDF Reader Agent Node (pdf_agent_node -> __end__)"""
    time_table["pdf_agent"] = time.time()

    state["current_agent"] = "pdf_reader_agent"
    user_message = state["question"].content

    template =  """
                    Given the following extracted parts of a pdf document and a question, create a final answer with references ("sources"). 
                    If you don't know the answer, just say that you don't know. Don't try to make up an answer.
                    ALWAYS return a "sources" part in your answer. Sources is a identifier for the source of the information that you got the answer from.
                    Always return a "process" part in your answer. Describe how you got the answer, and place it in the "process" part. Ensure that process starts with <_START_> and ends with <_END_>.

                    QUESTION: {question}
                    =========
                    {summaries}
                    =========
                    process:
                    answer : 
                    sources :
                """
    
    PROMPT = PromptTemplate(template=template, input_variables=["summaries", "question"])

    chain_type_kwargs = {"prompt": PROMPT}

    chain_window = RetrievalQAWithSourcesChain.from_chain_type(
        ChatOpenAI( temperature=0,
                    openai_api_key=openai_var.openai_api_key,
                    openai_api_base=openai_var.openai_endpoint,
                    model=openai_var.openai_model
                    ), 
        chain_type = "stuff", 
        retriever = kg_retrieval_window(state["pdf_name"]),
        chain_type_kwargs = chain_type_kwargs,
        return_source_documents = True
    )

    answer = chain_window(
        {"question": user_message},
        return_only_outputs=True,
        )
    
    result_message = AIMessage(content=answer["answer"])
    state["answer"] = result_message
    state["messages"].append(result_message)
    state["agent_scratchpads"].append(answer["source_documents"])
    state["next_agent"] = "pdf_validator"

    return state

async def pdf_validator_node(state: MessageState) -> MessageState:
    """PDF Validator Node (pdf_agent_node -> pdf_validator_node -> __end__)"""
    start_time = time.time()

    state["current_agent"] = "pdf_validator"

    user_message = state["question"].content
    ai_message = state["answer"].content
    agent_scratchpad = state["agent_scratchpads"][-1]

    parser = JsonOutputParser(pydantic_object=Route)
    
    prompt = ChatPromptTemplate.from_messages([
            ("system",
            "Return in json format:\n"
            "{{\"current_agent\": \"sql_validator\", \"next_agent\": \"__end__\", \"question\": \"question_text\", \"answer\": \"<_START_> answer_text <_END_>\"}}\n\n"
            "You are a QC analyst with expertise in understanting customer requests. Your task is to validate the answer to the user's question based on the information in the agent scratchpad.\n\n" 
            "In addition, you are also responsible for providing additional information to the user to ensure they have plenty of information.\n\n"
            "The user's last request:\n{user_message}\n\n"
            "Here is the message from the agent:\n{ai_message}. \n\n"
            "Look at the agent scratchpad: {agent_scratchpad}. \n\n"
            "Ensure the answer is correct and informative based on the agent's question and the information in the agent scratchpad. If the answer is correct, then simply return the message {ai_message}. If the answer is not specific enough, and requires a more indepth analyis, then let the user know. \n\n")
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

    end_time = time.time()
    time_table["pdf_validator"] = (end_time - start_time)

    return state


async def call_sql_agent(state: MessageState) -> MessageState:

    db_for_table = SQLDatabase.from_uri(postgres_var.db_url, include_tables=[state["table_name"]])
    toolkit = SQLDatabaseToolkit(db=db_for_table, llm=model)
    sql_agent_for_table = create_sql_agent(llm=model, toolkit=toolkit, agent_type="openai-tools", verbose=False, agent_executor_kwargs={"return_intermediate_steps": True})

    question = state["question"]
    sql_result = await sql_agent_for_table.ainvoke(question)

    return sql_result

async def sql_agent_node(state: MessageState) -> MessageState:
    """SQL Agent Node (SQL Agent Node -> SQL Validator -> __end__)"""
    time_table["sql_agent"] = time.time()

    sql_result = await call_sql_agent(state)
    state["current_agent"] = "sql_agent"
    intermediate_steps = sql_result.get("intermediate_steps", [])
    intermediate_steps = format_to_openai_tool_messages(intermediate_steps)

    query_arg = None
    for step in intermediate_steps:
        if isinstance(step, AIMessageChunk):
            tool_call = step.tool_calls[0]
            tool_chunk = step.tool_call_chunks[0]
            if "query" in tool_call["args"]:
                query_arg = tool_call["args"]["query"]

    parser = JsonOutputParser(pydantic_object=Route)
    
    prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are a SQL expert. You are the SQL agent of a conversation whose generated queries will help visualize the answer to the user's question.\n\n"
            "The question is: {question}\n\n"
            "The answer is: {answer}\n\n"
            "The query is: {query_arg}\n\n"
            "The database columns and types are: {columns_and_types} for you to use.\n\n"
            ""
            "You will be provided with a query and a user question. Your task is to generate a new query that will help visualize the answer to the user's question:\n"
            "1. If it is an aggregate query, modify the query to include 'ctid' by using 'GROUP BY' appropriately. Make sure to include the valid column name/names from {columns_and_types} and use llm_count as a variable for COUNT.\n"
            "2. If it is not an aggregate query, modify the query to include 'ctid' dynamically in the SELECT clause along with the column name/names from {columns_and_types}.\n"
            "3. Make sure to choose the approprate ctid column based on the table schema and the user's question.\n"
            "4. Create a label(max 7 words) with the word select. For example, 'Select all items', 'Select the items', etc..\n\n"
            "Return in json format with original query in 'answer', modified query in 'modified_query' and a label in 'modified_query_label':\n"
            "{{\"current_agent\": \"sql_agent\", \"next_agent\": \"sql_agent\", \"question\": \"None\", \"answer\": \"<_START_> {answer} \\n\\n Query: {query_arg} <_END_>\", \"modified_query\": \"Modified Query\", \"modified_query_label\": \"modified query label\"}}\n\n")
        ])
    
    inputs = { "query_arg": query_arg, "answer": sql_result["output"], "question": state["question"].content, "columns_and_types": state["columns_and_types"]}

    chain = prompt | model | parser
    response = await chain.ainvoke(inputs)


    query_message = AIMessage(content=query_arg)
    modified_query = response["modified_query"]
    modified_query_label = response["modified_query_label"]
    mod_query_dict = f"modified_query: {modified_query}, modified_query_label: {modified_query_label}"
    result_message = AIMessage(content= sql_result["output"])
    state["answer"] = result_message
    state["messages"].append(query_message)
    state["messages"].append(AIMessage(content=mod_query_dict))
    state["messages"].append(result_message)
    state["agent_scratchpads"].append(intermediate_steps)
    state["next_agent"] = "__end__"

    return state


async def sql_validator_node(state: MessageState) -> MessageState:
    """SQL Validator Node (SQL Agent Node -> SQL Validator -> __end__)"""
    time_table["sql_validator"] = time.time()

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
    time_table["data_analyst"] = time.time()

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

    if parsed_result["question"] != "":
        state["messages"].append(AIMessage(content=f"{parsed_result["question"]}"))
    state["answer"] = AIMessage(content=f"{parsed_result['answer']}")

    if parsed_result["next_agent"] == "human_input":
        return Command(goto="human_input")
    else:
        print("END OF HUMAN IN THE LOOP")
        state["next_agent"] = parsed_result["next_agent"]
        state["messages"].append(AIMessage(content=f"{parsed_result['answer']}"))
        return state

async def human_input(state: MessageState):
    """Human Input Node to get user input and communicate with Data Analyst"""

    human_message = interrupt("human_input")

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
    time_table["cleanup"] = time.time()
    return {"messages": [], "next_agent": "__end__"}

# --- Build the State Graph ---
workflow = StateGraph(state_schema=MessageState)

# Nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("pdf_agent", pdf_agent_node)
workflow.add_node("pdf_validator", pdf_validator_node)
workflow.add_node("sql_agent", sql_agent_node)
workflow.add_node("sql_validator", sql_validator_node)
workflow.add_node("data_analyst", data_analyst_node)
workflow.add_node("human_input", human_input)
workflow.add_node("cleanup", cleanup_node)
# Edges
workflow.add_edge(START, "supervisor")
workflow.add_edge("pdf_agent", "pdf_validator")
workflow.add_edge("pdf_validator", END)
workflow.add_edge("sql_agent", END)
workflow.add_edge("data_analyst", END)
workflow.add_edge("human_input", "data_analyst")

workflow.add_conditional_edges("supervisor", lambda state: state["next_agent"])


memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


class ChatbotManager:
    def __init__(self):
        self.chatbots: Dict[str, Dict[str, List[BaseMessage]]] = {}


    async def create_chatbot(self, session: str, language: str):
        if session in self.chatbots:
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
            self.chatbots[session]["table_name"] = table_name
            self.chatbots[session]["columns_and_types"] = get_all_columns_and_types(table_name, db)
        
        except Exception as e:
            raise RuntimeError(f"Failed to add or replace Table name for session {session}: {e}")
        

    async def alter_pdf_name(self, session: str, pdf_name: str):
        try:
            rprint(f"Adding or replacing PDF name for session {session}: {pdf_name}")
            rprint(self.chatbots[session])
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
            return None
            
        return self.chatbots[session_id]["columns_and_types"]
    

manager = ChatbotManager()
message_queue = asyncio.Queue()


async def safe_send(message: dict, session_id: str):
    try:
        websocket = active_websockets[session_id]
    except KeyError:
        rprint(websocket.client_state)
        logging.warning("Attempted to send a message on a closed WebSocket.")
        return
    
    if websocket.client_state.name == "CONNECTED":
        await websocket.send_json(message)
    else:
        rprint(websocket.client_state)
        logging.warning("Attempted to send a message on a closed WebSocket.")


async def start_chatbot(session: str):
    await manager.create_chatbot(session, "English")


async def alter_table_name(session: str, table_name: str):
    print(f"Adding SQL agent for session_id: {session} and table_name: {table_name}")
    await manager.alter_table_name(session, table_name)


async def alter_pdf_name(session: str, pdf_name: str):
    print(f"Adding SQL agent for session_id: {session} and pdf_name: {pdf_name}")
    await manager.alter_pdf_name(session, pdf_name)


async def run_chatbots( session_id: str):
    chatbot = await manager.get_chatbot(session_id)
    config = chatbot["config"]

    while True:   
        try:
            # Wait for a new message (blocking until available)
            rprint("Waiting for a new message...")
            message = await message_queue.get()
            logging.debug(f"Processing message: {message}, Queue size: {message_queue.qsize()}")

            state = {
                "current_agent": None,
                "next_agent": "supervisor",
                "question": HumanMessage(content=message),
                "answer": None,
                "table_name": await manager.get_chatbot_table_name(session_id),
                "pdf_name": await manager.get_chatbot_pdf_name(session_id),
                "messages": [HumanMessage(content=message)],
                "agent_scratchpads": [],
                "columns_and_types": await manager.get_chatbot_columns_and_types(session_id)
            }

            is_interrupted = False
            while_loop = True
            cur_agent = None
        
            words_to_find = ['<_START_>', '<_']
            word_buffer = ""
            word_state = False
            str_response = []
            char_backlog = []
            query = None

            input_arg = state
        

            while while_loop:
                if is_interrupted:
                    print("Interrupted: ", len(interrupts.tasks), "Current agent: ", cur_agent)
                    message = await message_queue.get()
                    message = {
                                        "event": "on_chain_start",
                                        "message": "",
                                        "table_name": await manager.get_chatbot_table_name(session_id),
                                        "pdf_name": await manager.get_chatbot_pdf_name(session_id),
                                        "role": next_agent,
                                    }
                    rprint("on_chain_start: ", message)
                    await safe_send(message, session_id)
                    logging.debug(f"Processing message: {message}, Queue size: {message_queue.qsize()}")
                    input_arg = Command(resume=message)

                async for event in app.astream_events(input_arg, config, version="v2"):
                    if event.get("event") == "on_chain_start":
                        data = event.get("data", {})     
                        if isinstance(data, dict) and "input" in data:
                            input_data = data["input"]
                            if isinstance(input_data, dict) and "next_agent" in input_data:
                                next_agent = input_data["next_agent"]
                                if cur_agent != next_agent:
                                    # rprint("on_chain_start: ", cur_agent)
                                    cur_agent = next_agent
                                    if cur_agent != "__end__":
                                        message = {
                                            "event": "on_chain_start",
                                            "message": "",
                                            "table_name": await manager.get_chatbot_table_name(session_id),
                                            "pdf_name": await manager.get_chatbot_pdf_name(session_id),
                                            "role": next_agent,
                                            "time": str( math.trunc((time_table[str(next_agent)]) * 1000/ 1000)),
                                            "modified_query": "",
                                            "modified_query_label": ""

                                        }
                                        await safe_send(message, session_id)


                    if event["event"] == "on_chain_error":
                        print("Error: ", event["data"])
                    if event["event"] == "on_chat_model_stream":
                        prev_char_backlog = char_backlog.copy()

                        word_buffer, word_state, str_response, char_backlog = process_stream_event(
                            event, words_to_find, word_buffer, word_state, str_response, char_backlog
                        )
                        if word_state and len(str_response) > 0 and prev_char_backlog == char_backlog:
                            role = event['metadata']['langgraph_node']
                            end_time = time.time()
                            message = {"event": "on_chat_model_stream", 
                                        "message": word_buffer,
                                        "table_name": await manager.get_chatbot_table_name(session_id),
                                        "pdf_name": await manager.get_chatbot_pdf_name(session_id),
                                        "role": role,
                                        "time": str( math.trunc((end_time - time_table[str(role)]) * 1000/ 1000)),
                                        "modified_query": "",
                                        "modified_query_label": ""
                                        }
                            # rprint(message)
                            await safe_send(message, session_id)

                    if event["event"] == "on_chain_end" and not is_interrupted:
                        if "output" in event['data']:
                            if 'modified_query' in event['data']['output']:
                                end_time = time.time()
                                message = {"event": "on_chain_end", 
                                            "message": "", 
                                            "table_name": await manager.get_chatbot_table_name(session_id),
                                            "pdf_name": await manager.get_chatbot_pdf_name(session_id),
                                            "role": role,
                                            "time": str(math.trunc((end_time - time_table[str(role)]) * 1000)/ 1000),
                                            "modified_query": str(event['data']['output']['modified_query']),
                                            "modified_query_label": str(event['data']['output']['modified_query_label'])
                                            }
                                await safe_send(message, session_id)
                                time_table[str(role)] = 0

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

        except Exception as e:
            logging.error(f"Error in chatbot processing: {e}")
            break
        finally:
            if session_id in tasks:
                del tasks[session_id]
                print(f"Task for session_id {session_id} removed")






def find_word_in_text( word, words_to_find, word_buffer):
    # print( "input word: ", word )
    for word_to_find in words_to_find:
        if word_to_find in word_buffer:
            return [True, word_to_find]
    return [False, None]

def update_word_state(find_word, words_to_find, word_buffer, word_state):
    """Update the word state based on the matched word."""
    if find_word in ["<_START_>"]:
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

    word_buffer = word_buffer.replace("\\n\\n", "<br/><br/>").replace("\\n", "<br/>")

    # rprint("Word (raw):", repr(word))
    # rprint("Word Buffer (raw):", repr(word_buffer))
    # rprint("Word: ", word)
    # rprint("Word Buffer: ", word_buffer)


    find_word = find_word_in_text(word, words_to_find, word_buffer)

    # Update word state
    word_state, word_buffer = update_word_state(find_word[1], words_to_find, word_buffer, word_state)

    # rprint("Word Buffer: ", word_buffer)

    # Process response if in word state
    if word_state:
        str_response, char_backlog = process_response(word, str_response, char_backlog)
    else:
        str_response = []
        
    word_state, char_backlog = handle_finish_reason(event, word_state, char_backlog)

    return word_buffer, word_state, str_response, char_backlog

