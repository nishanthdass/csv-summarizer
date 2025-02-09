from models.models import MessageState
from llm_core.src.prompt_engineering.templates import *
from llm_core.src.prompt_engineering.chains import json_parser_prompt_chain, trimmer, kg_retrieval_chain
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, AIMessageChunk
from rich import print as rprint
from llm_core.src.prompt_engineering.chains import call_sql_agent
from langgraph.types import interrupt, Command
import json
import time
import logging


time_table = { "supervisor": 0, "pdf_agent": 0, "pdf_validator": 0, "call_sql_agent": 0, "sql_agent": 0, "sql_validator": 0, "data_analyst": 0, "human_input": 0, "cleanup": 0}


# --- Define Node Functions ---
async def supervisor_node(state: MessageState) -> MessageState:
    """Supervisor Node to route questions to agents."""
    time_table["supervisor"] = time.time()
    state["current_agent"] = "supervisor"
    if state["next_agent"] != "supervisor":
        return {"messages": state["messages"], "next": state["next"]}

    conversation_history = state["messages"]
    trimmed_messages = trimmer(state)

    if state["table_name"] is None and state["pdf_name"] is None:
        prompt = NEITHERTABLEORPDFPROMPTTEMPLATE

    elif state["table_name"] is None and state["pdf_name"] is not None:
        prompt = PDFONLYPROMPTTEMPLATE

    elif state["table_name"] is not None and state["pdf_name"] is None:
        prompt = TABLEONLYPROMPTTEMPLATE

    elif state["table_name"] is not None and state["pdf_name"] is not None:
        prompt = TABLEANDPDFPROMPTTEMPLATE


    inputs = {
        "user_message": trimmed_messages[-1].content if trimmed_messages else "",
        "table_name": state["table_name"],
        "pdf_name": state["pdf_name"],
        "conversation_history": conversation_history
    }

    model = "gpt-4o"

    try:
        response = await json_parser_prompt_chain(prompt, model, inputs)
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
        return state
    

async def pdf_agent_node(state: MessageState) -> MessageState:
    """PDF Reader Agent Node (pdf_agent_node -> __end__)"""
    time_table["pdf_agent"] = time.time()

    state["current_agent"] = "pdf_reader_agent"
    user_message = state["question"].content

    answer = kg_retrieval_chain(user_message, PDFAGENTPROMPTTEMPLATE, state=state)
    
    result_message = AIMessage(content=answer["answer"])
    state["answer"] = result_message
    state["messages"].append(result_message)
    state["agent_scratchpads"].append(answer["source_documents"])
    state["next_agent"] = "pdf_validator"

    return state



async def pdf_validator_node(state: MessageState) -> MessageState:
    """PDF Validator Node (pdf_agent_node -> pdf_validator_node -> __end__)"""
    time_table["pdf_validator"] = time.time()

    state["current_agent"] = "pdf_validator"

    user_message = state["question"].content
    ai_message = state["answer"].content
    agent_scratchpad = state["agent_scratchpads"][-1]

    
    # print("agent_scratchpad", state["agent_scratchpads"])
    inputs = { "ai_message": ai_message,
                "agent_scratchpad": agent_scratchpad,
                "user_message": user_message}

    model = "gpt-4o"


    response = await json_parser_prompt_chain(PDFVALIDATORPROMPTTEMPLATE, model, inputs)
    
    state["messages"].append(AIMessage(content=response["answer"]))
    state["answer"] = AIMessage(content=response["answer"])
    state["next_agent"] = response["next_agent"]

    return state



async def sql_agent_node(state: MessageState) -> MessageState:
    """SQL Agent Node (SQL Agent Node -> SQL Validator -> __end__)"""

    state["current_agent"] = "sql_agent"

    time_table["sql_agent"] = time.time()
    model = "gpt-4o-mini"

    sql_result = await call_sql_agent( model, state)

    response = sql_result["output"]
    response = response.replace("```json", "").replace("```", "")

    response = json.loads(response)

    answer_query = response["answer_query"]
    viewing_query_label = response["viewing_query_label"]
    mod_query_dict = f"answer_query: {answer_query}, viewing_query_label: {viewing_query_label}"

    state["answer_query"] = answer_query
    state["viewing_query_label"] = viewing_query_label
    state["has_function_call"] = True
    state["function_call"] = "sql_query"

    state["messages"].append(AIMessage(content=mod_query_dict))
    state["next_agent"] = "__end__"

    return state




async def data_analyst_node(state: MessageState) -> MessageState:
    """Data Analyst Node ((Data Analyst Node <->  Human Input) -> Cleanup -> __end__)"""
    
    time_table["data_analyst"] = time.time()
    trimmed_messages = trimmer(state)

    inputs = {
        "user_message": trimmed_messages,
        "table_name": state["table_name"]
    }
    model = "gpt-4o"

    parsed_result = await json_parser_prompt_chain(DATAANALYSTPROMPTTEMPLATE, model, inputs)

    if parsed_result["question"] != "":
        state["messages"].append(AIMessage(content=f"{parsed_result["question"]}"))
    state["answer"] = AIMessage(content=f"{parsed_result['answer']}")

    if parsed_result["next_agent"] == "human_input":
        return Command(goto="human_input")
    else:
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
