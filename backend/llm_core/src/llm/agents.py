from models.models import MessageState
from llm_core.src.prompt_engineering.templates import *
from llm_core.src.prompt_engineering.chains import json_parser_prompt_chain, trimmer, kg_retrieval_chain
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, AIMessageChunk
from rich import print as rprint
from llm_core.src.prompt_engineering.chains import call_sql_agent, call_sql_manipulator_agent
from langgraph.types import interrupt, Command
from llm_core.src.llm.function_layer import sql_agent_function
import time
import logging
import json
import re


time_table = { "supervisor": 0, "pdf_agent": 0, "call_sql_agent": 0, "sql_agent": 0, "sql_manipulator_agent": 0, "data_analyst": 0, "human_input": 0, "cleanup": 0}


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

    # rprint("Conversation History: ", conversation_history)
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


async def sql_manipulator_agent_node(state: MessageState) -> MessageState:
    """SQL Manipulator Agent Node (sql_manipulator_agent_node -> __end__)"""
    time_table["sql_manipulator_agent"] = time.time()
    state["current_agent"] = "sql_manipulator_agent"
    user_message = state["question"].content

    model = "gpt-4o"

    try:
        action = await call_sql_manipulator_agent(model, state)
        response = action["output"]
        match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)

        if match:
            json_str = match.group(1).strip()  # Extract JSON part only
            response = json.loads(json_str)
        else:
            raise json.JSONDecodeError("No valid JSON found", response, 0)
    except Exception as e:
        logging.error(f"Error invoking chain: {e}")
        response = None

    if response["status"] == "success":
        state["messages"].append(AIMessage(content=response['answer'] + response['answer_query']))

        state["answer_query"] = response["answer_query"]
        state["answer"] = AIMessage(content=response["answer"])
        state["has_function_call"] = True
        state["function_call"] = "sql_manipulator_query"
        state["viewing_query_label"] = response["viewing_query_label"]
    else:
        state["messages"].append(AIMessage(content=response))
        state["answer"] = AIMessage(content=response["answer"])

    state["next_agent"] = "__end__"
    return state


async def sql_agent_node(state: MessageState) -> MessageState:
    """SQL Agent Node (SQL Agent Node -> SQL Validator -> __end__)"""
    rprint("SQL Agent Node")
    # rprint("State: ", state)

    state["current_agent"] = "sql_agent"

    time_table["sql_agent"] = time.time()

    model = "gpt-4o"

    try:
        if state["next_agent"] != "human_input":
            # rprint("Calling SQL Agent: ", state["next_agent"])
            sql_result = await call_sql_agent(model, state)
            response = sql_result["output"]
            # rprint("Response from SQL Agent: ", response)
            match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()  # Extract JSON part only
                response = json.loads(json_str)
            state["next_agent"] = response["next_agent"]
            rprint("Next Agent: ", state["next_agent"])
            if state["next_agent"] == "human_input":
                    state["agent_step"] = 4
                    rprint("Agent Step after Calling SQL Agent: ", state["agent_step"])
            state["messages"].append(AIMessage(content=response["answer"]))
            
            # rprint("After Calling SQL Agent: ", state["next_agent"])
        else:
            raise json.JSONDecodeError("No valid JSON found", response, 0)

    except json.JSONDecodeError:
        rprint(f"JSONDecodeError: {response}")
        state["messages"].append(AIMessage(content=response))
        state["answer"] = AIMessage(content=response)
        if state["is_multiagent"] is True:
            state["next_agent"] = "data_analyst"
        else:
            state["next_agent"] = "__end__"

        return state
    
    state["query_type"] = response["query_type"]

    # rprint("state['next_agent']: ", state["next_agent"])

    try:
        if state["query_type"] == "retrieval":
            answer_retrieval_query = response["answer_retrieval_query"]
            visualize_retrieval_query = response["visualize_retrieval_query"]
            visualize_retrieval_label = response["visualize_retrieval_label"]
            
            retrival_query_result = sql_agent_function(table_name=state["table_name"], query=answer_retrieval_query, role=state["current_agent"])
            rprint("Next Agent: ", state["next_agent"])
            if state["next_agent"] == "human_input":
                state["agent_step"] = 4
                rprint("Agent Step after sql_agent_function: ", state["agent_step"])
            if "Error" not in retrival_query_result:
                successful_query = "Query Successful: " + retrival_query_result["Result"]
                state["messages"].append(AIMessage(content=successful_query + " when using query: " + answer_retrieval_query))
                state["answer_retrieval_query"] = answer_retrieval_query
                state["visualize_retrieval_query"] = visualize_retrieval_query
                state["visualize_retrieval_label"] = visualize_retrieval_label
                state["has_function_call"] = True
                state["query_failed"] = False
                if state["is_multiagent"] is True:
                    state["agent_step"] = 4
            else:
                agent_notes = "<START> Query Error: " + retrival_query_result["Error"] + " when using query: " + answer_retrieval_query + " <END>"
                state["messages"].append(AIMessage(content=agent_notes))
                state["query_failed"] = True
                state["has_function_call"] = True
                state["answer_retrieval_query"] = answer_retrieval_query
                if state["is_multiagent"] is True:
                    state["agent_step"] = 3

            
            if state["is_multiagent"] is True:
                state["agent_scratchpads"].append(AIMessage(content=agent_notes))


    except Exception as e:
        rprint(f"Unexpected error: {str(e)}")

    if state["is_multiagent"] is True:
        state["next_agent"] = "data_analyst"
    
    if state["next_agent"] == "human_input":
        # rprint("State['messages']: ", state["messages"])
        rprint("Interupt in Human Input Node")
        return Command(goto="human_input", update={"agent_step": 4})    
    else:
        state["next_agent"] = "__end__"
    
    return state


async def data_analyst_node(state: MessageState) -> MessageState:
    """Data Analyst Node ((Data Analyst Node <->  Human Input) -> Cleanup -> __end__)"""
    rprint("Data Analyst Node")
    
    time_table["data_analyst"] = time.time()
    trimmed_messages = trimmer(state)

    if len(state["agent_scratchpads"]) > 0: 
        agent_scratchpad = state["agent_scratchpads"][-1]
    else:
        agent_scratchpad = ""

    inputs = {
        "agent_step": state["agent_step"],
        "agent_scratchpads": agent_scratchpad,
        "user_message": trimmed_messages,
        "pdf_name": state["pdf_name"],
        "columns_and_types": state["columns_and_types"],
        "table_name": state["table_name"],
    }
    model = "gpt-4o"

    # rprint("inputs step: ", state["agent_step"])
    # rprint("inputs agent_scratchpads: ", agent_scratchpad)
    parsed_result = await json_parser_prompt_chain(DATAANALYSTPROMPTTEMPLATE, model, inputs)
    # rprint("parsed_result: ", parsed_result)

    state["messages"].append(AIMessage(content=f"{parsed_result['answer']}"))
    state["messages"].append(AIMessage(content=f"{parsed_result["question"]}"))
    state["answer"] = AIMessage(content=f"{parsed_result['answer']}")
    state["question"] = AIMessage(content=f"{parsed_result['question']}")
    state["is_multiagent"] = bool(parsed_result["is_multiagent"])

    if parsed_result["next_agent"] == "human_input":
        rprint("Interupt in Data Analyst Node")
        return Command(goto="human_input", state=state)
    else:
        state["next_agent"] = parsed_result["next_agent"]
        # rprint("parsed_result: ", parsed_result)
        # rprint("next agent: ", state["next_agent"])
        return state


async def human_input(state: MessageState):
    """Human Input Node to get user input and communicate with Data Analyst"""
    rprint("Human Input Node")
    rprint("human_input State: ", state)

    human_message = interrupt("human_input")

    rprint("Human Message: ", human_message)
    state["messages"].append(HumanMessage(content=human_message))
    state["next_agent"] = "sql_agent"
    state["agent_step"] = 4
    rprint("Agent Step after human_input: ", state["agent_step"])

    return state

async def cleanup_node(state: MessageState) -> MessageState:
    time_table["cleanup"] = time.time()
    rprint("Cleanup Node Messages: ", state["messages"])
    return state
