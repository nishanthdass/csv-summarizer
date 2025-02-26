from models.models import MessageState
from llm_core.src.prompt_engineering.templates import *
from llm_core.src.prompt_engineering.chains import json_parser_prompt_chain, trimmer, kg_retrieval_chain
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, AIMessageChunk
from rich import print as rprint
from llm_core.src.prompt_engineering.chains import call_sql_agent
from langgraph.types import interrupt, Command
from llm_core.src.llm.function_layer import sql_agent_function
import time
import logging
import json
import re


time_table = { "supervisor": 0, "pdf_agent": 0, "call_sql_agent": 0, "sql_agent": 0, "sql_validator": 0, "data_analyst": 0, "human_input": 0, "cleanup": 0}


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
        state["agent_step"] = 1


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

    state["current_agent"] = "pdf_agent"
    user_message = state["question"].content

    if state["is_multiagent"] is True:
        user_message = user_message + ", Columns: " + str(state["columns_and_types"])
        answer = kg_retrieval_chain(user_message, PDFAGENTPROMPTTEMPLATE_B, state=state)
        # rprint("pdf_agent: ", answer)
    else:
        answer = kg_retrieval_chain(user_message, PDFAGENTPROMPTTEMPLATE_A, state=state)

    result_message = AIMessage(content=answer["answer"])
    state["answer"] = result_message
    state["messages"].append(result_message)
    agent_scratchpad = answer["answer"]
    agent_scratchpad = agent_scratchpad.replace("<_START_>", "").replace("<_END_>", "")
    state["agent_scratchpads"].append(answer["answer"])
    if state["is_multiagent"] is True:
        state["next_agent"] = "data_analyst"
        state["agent_step"] = 2
    else:
        state["next_agent"] = "__end__"
    return state


async def sql_agent_node(state: MessageState) -> MessageState:
    """SQL Agent Node (SQL Agent Node -> SQL Validator -> __end__)"""

    state["current_agent"] = "sql_agent"

    time_table["sql_agent"] = time.time()
    if state["is_multiagent"] is True:
        model = "gpt-4o"
    else:
        model = "gpt-4o-mini"
    # model = "gpt-4o"
    try:
        rprint("state question: ", state["question"])
        sql_result = await call_sql_agent(model, state)
        
        response = sql_result["output"]

        # Extract JSON content between ```json and ```
        match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)

        if match:
            json_str = match.group(1).strip()  # Extract JSON part only
            response = json.loads(json_str)
        else:
            raise json.JSONDecodeError("No valid JSON found", response, 0)

    except json.JSONDecodeError:
        rprint(f"JSONDecodeError: {response}")


    answer_query = response["answer_query"]
    visualizing_query = response["visualizing_query"]
    viewing_query_label = response["viewing_query_label"]
    rprint("answer_query: ", answer_query)
    rprint("visualizing_query: ", visualizing_query)
    try:
        query_response = sql_agent_function(table_name=state["table_name"], query=answer_query)
        if "Error" not in query_response:
            state["agent_scratchpads"].append(query_response)
            if state["is_multiagent"] is True:
                state["agent_step"] = 3
        else:
            state["agent_scratchpads"].append("This query failed, try something else: " + answer_query)
        mod_query_dict = f"answer_query: {answer_query}, visualizing_query: {visualizing_query}, viewing_query_label: {viewing_query_label}"

        state["answer_query"] = answer_query
        state["visualizing_query"] = visualizing_query
        state["viewing_query_label"] = viewing_query_label
        state["has_function_call"] = True
        state["function_call"] = "sql_query"

        state["messages"].append(AIMessage(content=mod_query_dict))

    except Exception as e:
        rprint(f"Unexpected error: {str(e)}")

    if state["is_multiagent"] is True:
        state["next_agent"] = "data_analyst"
    else:
        state["next_agent"] = "__end__"

    return state


async def data_analyst_node(state: MessageState) -> MessageState:
    """Data Analyst Node ((Data Analyst Node <->  Human Input) -> Cleanup -> __end__)"""
    
    time_table["data_analyst"] = time.time()
    trimmed_messages = trimmer(state)

    if len(state["agent_scratchpads"]) > 0: 
        agent_scratchpad = state["agent_scratchpads"][-1]
    else:
        agent_scratchpad = ""

    inputs = {
        "user_message": trimmed_messages,
        "conversation_history": state["messages"],
        "agent_scratchpads": agent_scratchpad,
        "pdf_name": state["pdf_name"],
        "columns_and_types": state["columns_and_types"],
        "table_name": state["table_name"],
        "agent_step": state["agent_step"]
    }
    model = "gpt-4o"

    rprint("inputs step: ", state["agent_step"])
    rprint("inputs agent_scratchpads: ", state["agent_scratchpads"])
    parsed_result = await json_parser_prompt_chain(DATAANALYSTPROMPTTEMPLATE, model, inputs)
    rprint("parsed_result: ", parsed_result)

    state["messages"].append(AIMessage(content=f"{parsed_result['answer']}"))
    state["messages"].append(AIMessage(content=f"{parsed_result["question"]}"))
    state["answer"] = AIMessage(content=f"{parsed_result['answer']}")
    state["question"] = AIMessage(content=f"{parsed_result['question']}")
    state["is_multiagent"] = bool(parsed_result["is_multiagent"])

    if parsed_result["next_agent"] == "human_input":
        rprint("Interupt in Data Analyst Node")
        return Command(goto="human_input")
    else:
        state["next_agent"] = parsed_result["next_agent"]
        # rprint("parsed_result: ", parsed_result)
        # rprint("next agent: ", state["next_agent"])
        return state


async def human_input(state: MessageState):
    """Human Input Node to get user input and communicate with Data Analyst"""
    rprint("Human Input Node")

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
