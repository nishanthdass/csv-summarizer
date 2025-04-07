from models.models import MessageState
from llm_core.src.prompt_engineering.templates import *
from llm_core.src.prompt_engineering.chains import json_parser_prompt_chain, trimmer, kg_retrieval_chain
from langchain_core.messages import HumanMessage
from rich import print as rprint
from llm_core.src.prompt_engineering.chains import call_sql_agent, json_parser_prompt_chain_data_analyst
from langgraph.types import interrupt, Command
from llm_core.src.utils.utility_function import *
from db.get_embeddings import get_similar_rows, get_all_columns_and_types_tuple
import time
import logging


time_table = { "pdf_agent": 0, "sql_agent": 0, "data_analyst": 0, "human_input": 0}


# --- Define Node Functions ---
async def sql_agent_node(state: MessageState) -> MessageState:
    """SQL Agent Node (SQL Agent Node -> __end__)"""
    time_table["sql_agent"] = time.time()
    state["current_agent"] = "sql_agent"

    try:
        question = state["question"].content
        if "augmented_question" in state and (state["augmented_question"] != "" and state["augmented_question"] is not None):
            question = state["augmented_question"]
        if state["query_type"] is None:
            input_variables={"input": question}
            response = await json_parser_prompt_chain(SQLQUERYTYPEAGENTPROMPTTEMPLATE, input_variables)
            await set_state(state, response)

    except Exception as e:
        logging.error(f"Error in sql_agent_node, issue finding query type: {e}")

    try:
        if state["next_agent"] != "human_input":
            trimmed_messages = trimmer(state)
            question = state["question"].content

            if state["query_type"] == "retrieval" and state["is_multiagent"] is True:
                question = state["augmented_question"]
                data_points = state["table_relevant_data"]
                prompt = await create_sql_multiagent_retrieval_prompt(question, data_points)

            if state["query_type"] == "retrieval" and state["is_multiagent"] is False:
                prompt = await create_sql_retrieval_prompt(question, last_message=trimmed_messages[-1], conversation_history=trimmed_messages)

            elif state["query_type"] == "manipulation": 
                prompt = await create_sql_manipulation_prompt(question, last_message=trimmed_messages[-1])

            sql_result = await call_sql_agent(prompt=prompt, state = state)
            response = await convert_to_dict(sql_result["output"])
            await set_state(state, response)

    except Exception as e:
        logging.error(f"Error in sql_agent_node, issue calling langchain sql_agent or parsing response: {e}")

    try:
        response = {}
        if state["query_type"] == "retrieval":
            answer_retrieval_query = state["answer_retrieval_query"]
            test_query_result = sql_agent_function(table_name=state["table_name"], query=answer_retrieval_query, role=state["current_agent"], query_type="retrieval")
            if "Result" in test_query_result:
                response["answer"] = "Query Successful when using query: " + answer_retrieval_query
                response["query_failed"] = False
                state["has_function_call"] = True
            else:
                response["answer"] = "<START> Query Error: " + test_query_result["Error"] + " when using query: " + answer_retrieval_query + " <END>"
                response["query_failed"] = True
                state["has_function_call"] = False

        elif state["query_type"] == "manipulation":
            perform_manipulation_query = str(state["perform_manipulation_query"])
            perform_manipulation_label = str(state["perform_manipulation_label"])
            if perform_manipulation_query != "" and perform_manipulation_label != "":
                response["answer"] = "Label: " + perform_manipulation_label + " Query: " + perform_manipulation_query
                response["has_function_call"] = True
            else:
                response["answer"] = "Unable to create Manipulation Query"
                response["has_function_call"] = False
        await set_state(state, response)

    except Exception as e:
        rprint(f"Unexpected error: {str(e)}")
    
    if state["next_agent"] == "human_input":
        query_type = state["query_type"]
        return Command(goto="human_input", update={"query_type": query_type})    
    else:
        state["next_agent"] = "__end__"

    return state


async def pdf_agent_node(state: MessageState) -> MessageState:
    """PDF Reader Agent Node (pdf_agent_node -> __end__)"""

    time_table["pdf_agent"] = time.time()
    state["current_agent"] = "pdf_agent"
    question = state["question"].content

    input_variables={"question": question, "pdf_name": state["pdf_name"]}
    answer = kg_retrieval_chain(PDFAGENTPROMPTTEMPLATE_A, input_variables)

    answer = await convert_to_dict(answer["answer"])

    response = {}
    response["answer"] = answer["answer"]
    response["next_agent"] = "__end__"


    state = await set_state(state, response)

    return state



async def data_analyst_node(state: MessageState) -> MessageState:
    """Data Analyst Node ((Data Analyst Node <->  Human Input) -> Cleanup -> __end__)"""

    table_name = state["table_name"]
    pdf_name = state["pdf_name"]
    time_table["data_analyst"] = time.time()
    question = state["question"].content

    columns = get_all_columns_and_types_tuple(table_name)
    col_str = ", ".join(item[0] for item in columns)

    # Get information from PDF KG
    input_variables={"question": question, "columns": col_str, "pdf_name": pdf_name}
    pdf_retrieval = kg_retrieval_chain(PDFAGENTPROMPTTEMPLATE_B, input_variables)
    pdf_retrieval_answer = await convert_to_dict(pdf_retrieval["answer"])

    answer = pdf_retrieval_answer["response"]
    data_points = pdf_retrieval_answer["data_points"]
    relevant_columns = pdf_retrieval_answer["relevant_columns"]

    # Get information from Table
    ranked_rows = get_similar_rows(table_name, data_points)
    similar_rows_str = ""
    for row in ranked_rows[:10]:
        similar_rows_str += " " + str(row[0]) + ": " + str(row[1]) + ", "

    inputs = {
        "question": question,
        "pdf_data": answer,
        "table_data": similar_rows_str
    }

    parsed_result = await json_parser_prompt_chain_data_analyst(inputs)

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
    human_message = interrupt("human_input")

    state["messages"].append(HumanMessage(content=human_message))
    state["next_agent"] = "sql_agent"

    return state
