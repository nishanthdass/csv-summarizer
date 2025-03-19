from models.models import MessageState
from langchain_openai import ChatOpenAI
from llm_core.src.prompt_engineering.templates import *
from langchain_core.tools import tool
from llm_core.src.prompt_engineering.chains import json_parser_prompt_chain, trimmer, kg_retrieval_chain, json_parser_prompt_chain_with_tools, kg_retrieval_column_chain
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, AIMessageChunk
from rich import print as rprint
from llm_core.src.prompt_engineering.chains import call_sql_agent, call_sql_manipulator_agent, find_query_type
from langgraph.types import interrupt, Command
from llm_core.src.llm.function_layer import sql_agent_function
from langchain_core.messages import ToolMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.prebuilt import create_react_agent
from langchain_core.runnables import RunnableConfig
from typing import Literal
from db.get_embedding_per_word import process_string_return_similarity, remove_duplicate_dicts
import json
import re
import time
import logging


time_table = { "supervisor": 0, "pdf_agent": 0, "call_sql_agent": 0, "sql_agent": 0, "sql_manipulator_agent": 0, "data_analyst": 0, "human_input": 0, "cleanup": 0}


# --- Define Node Functions ---

async def pdf_agent_node(state: MessageState) -> MessageState:
    """PDF Reader Agent Node (pdf_agent_node -> __end__)"""
    time_table["pdf_agent"] = time.time()

    state["current_agent"] = "pdf_agent"
    user_message = state["question"].content

    answer = kg_retrieval_chain(user_message, PDFAGENTPROMPTTEMPLATE_A, state=state)

    rprint("answer: ", answer)
    answer = answer["answer"].replace("<_START_>", "").replace("<_END_>", "")

    state["answer"] = AIMessage(content=answer)
    state["messages"].append(AIMessage(content=answer))
    state["agent_scratchpads"].append(answer)
    state["next_agent"] = "__end__"

    rprint("State after pdf_agent: ", state)
    return state


async def sql_agent_node(state: MessageState) -> MessageState:
    """SQL Agent Node (SQL Agent Node -> SQL Validator -> __end__)"""
    rprint("SQL Agent Node")

    state["current_agent"] = "sql_agent"

    time_table["sql_agent"] = time.time()

    model = "gpt-4o"

    try:
        question = state["question"].content
        if state["is_multiagent"] is True:
            # rprint(state)
            if "augmented_question" not in state:
                if state["augmented_question"]:
                    question = state["augmented_question"]
        if "query_type" not in state or (state["query_type"] not in ["retrieval", "manipulation"]):
            # rprint("Finding Query Type")
            response = await find_query_type(question)
            state["query_type"] = response["query_type"]

    except Exception as e:
        logging.error(f"Error invoking chain: {e}")

    try:
        if state["next_agent"] != "human_input":
            # rprint("Calling SQL Agent: ", state["query_type"])
            sql_result = await call_sql_agent(model, state)
            response = sql_result["output"]
            # rprint("Response from SQL Agent: ", response)
            match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1).strip()  # Extract JSON part only
                response = json.loads(json_str)
            # rprint("Response from SQL Agent: ", response)
            state["next_agent"] = response["next_agent"]
            state["query_type"] = response["query_type"]

            if state["next_agent"] == "human_input":
                    state["agent_step"] += 1
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

    try:
        if state["query_type"] == "retrieval":
            answer_retrieval_query = response["answer_retrieval_query"]
            visualize_retrieval_query = response["visualize_retrieval_query"]
            visualize_retrieval_label = response["visualize_retrieval_label"]
            
            retrival_query_result = sql_agent_function(table_name=state["table_name"], query=answer_retrieval_query, role=state["current_agent"], query_type="retrieval")
            if state["next_agent"] == "human_input":
                state["agent_step"] += 1
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

            
            # if state["is_multiagent"] is True:
            #     state["agent_scratchpads"].append(AIMessage(content=agent_notes))

        elif state["query_type"] == "manipulation":
            # rprint("response: ", response)
            if state["next_agent"] == "human_input":
                state["agent_step"] += 1
                rprint("Agent Step after sql_agent_function: ", state["agent_step"])
            perform_manipulation_query = response["perform_manipulation_query"]
            perform_manipulation_label = response["perform_manipulation_label"]
            if perform_manipulation_label != "":
                state["has_function_call"] = True
                state["perform_manipulation_query"] = perform_manipulation_query
                state["perform_manipulation_label"] = perform_manipulation_label
                agent_notes = response["answer"] + "Label: " + perform_manipulation_label + " Query: " + perform_manipulation_query
            else:
                agent_notes = response["answer"]
            state["messages"].append(AIMessage(content=agent_notes))
            state["answer"] = AIMessage(content=response["answer"])

    except Exception as e:
        rprint(f"Unexpected error: {str(e)}")

    if state["is_multiagent"] is True:
        state["next_agent"] = "data_analyst"
    
    if state["next_agent"] == "human_input":
        # rprint("State['messages']: ", state["messages"])
        rprint("Interupt in Human Input Node")
        # rprint("Agent Step: ", state["agent_step"])
        # rprint("Query Type: ", state["query_type"])
        agent_step = state["agent_step"]
        query_type = state["query_type"]
        return Command(goto="human_input", update={"agent_step": agent_step, "query_type": query_type})    
    else:
        state["next_agent"] = "__end__"
    
    # rprint("Final State: ", state)
    return state


async def data_analyst_node(state: MessageState) -> MessageState:
    """Data Analyst Node ((Data Analyst Node <->  Human Input) -> Cleanup -> __end__)"""
    rprint("Data Analyst Node")

    table_name = state["table_name"]
    time_table["data_analyst"] = time.time()
    trimmed_messages = trimmer(state)
    question = state["question"].content

    question = question
    columns = str(state["columns_and_types"])

    # Retreive exccerpt from PDF. 'answer' is summary and 'data_points' is list of data points
    pdf_retrieval = kg_retrieval_chain(question, PDFAGENTPROMPTTEMPLATE_B, state=state)
    rprint("pdf_retrieval: ", pdf_retrieval)
    rprint("keys: ", pdf_retrieval.keys())


    pdf_retrieval_answer = pdf_retrieval["answer"]
    match = re.search(r'```json\s*(\{.*?\})\s*```', pdf_retrieval_answer, re.DOTALL)
    if match:
        json_str = match.group(1).strip()  # Extract JSON content
        try:
            pdf_retrieval_answer = json.loads(json_str)  # Convert to dict
        except json.JSONDecodeError as e:
            print("JSON parsing error:", e)
            pdf_retrieval_answer = {}
    else:
        try:
            pdf_retrieval_answer = json.loads(pdf_retrieval_answer)  # Convert to dict
        except json.JSONDecodeError as e:
            print("JSON parsing error:", e)
            pdf_retrieval_answer = {}


    answer = pdf_retrieval_answer["answer"]
    data_points = pdf_retrieval_answer["data_points"]

    similar_rows = process_string_return_similarity(data_points, table_name)
    similar_rows = remove_duplicate_dicts(similar_rows)
    
    similar_rows_str = ""
    for row in similar_rows[:5]:
        similar_rows_str += "Column Name: " + str(row['columnName']) + ": " + str(row['value']) + ", "

    agent_note = answer +  "The most relevant data points from the pdf are: " + str(data_points) + ". The most similar data points from the table are: " + str(similar_rows_str) + ". "

    agent_scratchpad = AIMessage(content=agent_note)

    inputs = {
        "agent_scratchpads": agent_scratchpad,
        "question": question,
        "pdf_name": state["pdf_name"],
        "table_name": state["table_name"],
    }
    model = "gpt-4o"

    parsed_result = await json_parser_prompt_chain(DATAANALYSTMULTIAGENTPROMPTTEMPLATE, model, inputs)
    rprint("parsed_result: ", parsed_result)

    if parsed_result["next_agent"] == "human_input":
        rprint("Interupt in Data Analyst Node")
        return Command(goto="human_input", state=state)
    else:
        state["next_agent"] = parsed_result["next_agent"]
        state["is_multiagent"] = True
        state["augmented_question"] = parsed_result["augmented_question"]
        state["table_relevant_data"] = similar_rows_str
        state["pdf_relevant_data"] = data_points
        return state


async def human_input(state: MessageState):
    """Human Input Node to get user input and communicate with Data Analyst"""
    rprint("Human Input Node")

    human_message = interrupt("human_input")

    state["messages"].append(HumanMessage(content=human_message))
    state["next_agent"] = "sql_agent"
    state["agent_step"] += 1
    # rprint("Agent Step after human_input: ", state["agent_step"])

    return state
