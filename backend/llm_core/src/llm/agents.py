from models.models import MessageState
from llm_core.src.prompt_engineering.templates import *
from llm_core.src.prompt_engineering.chains import json_parser_prompt_chain, trimmer, kg_retrieval_chain
from langchain_core.messages import HumanMessage
from rich import print as rprint
from llm_core.src.prompt_engineering.chains import call_sql_agent, json_parser_prompt_chain_data_analyst
from langgraph.types import interrupt, Command
from llm_core.src.utils.utility_function import *
from db.tabular.postgres_utilities import get_all_columns_and_types
from db.get_embeddings import levenshtein_dist_from_db
import time
import logging

# --- Provides response time tracking for each agent ---
time_table = { "pdf_agent": 0, "sql_agent": 0, "data_analyst": 0, "human_input": 0}


# --- Define Agents ---
async def sql_agent_node(state: MessageState) -> MessageState:
    """SQL Agent takes a question and relevent data points as input and generates a SQL query to answer the question."""
    time_table["sql_agent"] = time.time()
    state["current_agent"] = "sql_agent"

    # Get query type if not already set by another agent
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

            # Use the augmented question and get supporting data points from last agent 
            if state["query_type"] == "retrieval" and state["is_multiagent"] is True:
                question = state["augmented_question"]
                data_points = state["table_relevant_data"]
                rprint("question: ", question)
                rprint("data_points: ", data_points)
                prompt = await create_sql_multiagent_retrieval_prompt(question, data_points)

            # Below conditions occur when the user directly communicates with the SQL Agent without going through any other agent
            if state["is_multiagent"] is False:
                if state["query_type"] == "retrieval":
                    prompt = await create_sql_retrieval_prompt(question, last_message=trimmed_messages[-1], conversation_history=trimmed_messages)
                elif state["query_type"] == "manipulation": 
                    prompt = await create_sql_manipulation_prompt(question, last_message=trimmed_messages[-1])

            # Call the SQL LLM Chain
            sql_result = await call_sql_agent(prompt=prompt, state = state)
            response = await convert_to_dict(sql_result["output"])
            await set_state(state, response)

    except Exception as e:
        logging.error(f"Error in sql_agent_node, issue calling langchain sql_agent or parsing response: {e}")

    # Present the results to the frontend
    try:
        response = {}
        if state["query_type"] == "retrieval":
            answer_retrieval_query = state["answer_retrieval_query"]
            # Test the query provided by the SQL Agent
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
    
    # Set next agent to human input in case SQL Agent needs more information from the user. This is determined by LLM.
    if state["next_agent"] == "human_input":
        query_type = state["query_type"]
        return Command(goto="human_input", update={"query_type": query_type})    
    else:
        state["next_agent"] = "__end__"

    return state


async def pdf_agent_node(state: MessageState) -> MessageState:
    """PDF agent takes a question and returns the answer to the question along with data points from the PDF."""
    time_table["pdf_agent"] = time.time()
    state["current_agent"] = "pdf_agent"
    question = state["question"].content

    input_variables={"question": question, "pdf_name": state["pdf_name"]}
    # response includes answer and next_agent
    response = kg_retrieval_chain(PDFAGENTPROMPTTEMPLATE_A, input_variables)

    answer = await convert_to_dict(response["answer"])

    response = {}
    response["answer"] = answer["answer"]
    response["next_agent"] = "__end__"

    state = await set_state(state, response)

    return state



async def data_analyst_node(state: MessageState) -> MessageState:
    """
    Retrieve and cross-reference information from both a PDF knowledge graph and a database table 
    to augment the user's question with relevant data points.

    This node performs the following steps:
      1. Extracts the table name, PDF name, and user question from the provided state.
      2. Retrieves all columns from the specified database table.
      3. Queries the PDF knowledge graph using cosine similarity to find relevant information 
         based on the user’s question.
      4. Parses the PDF response, extracts an answer, data points, and suggested relevant columns.
      5. Uses Levenshtein distance to match the PDF’s data points against rows in the database table, 
         focusing on the columns identified as relevant.
      6. Integrates the matched table data and the PDF data points into the user's question 
      7. Returns the updated message state, which includes the augmented question
    """
        
    table_name = state["table_name"]
    pdf_name = state["pdf_name"]
    time_table["data_analyst"] = time.time()
    question = state["question"].content

    columns = get_all_columns_and_types(table_name)
    col_str = ", ".join(item[0] for item in columns)

    # Get information from PDF KG
    input_variables={"question": question, "columns": col_str, "pdf_name": pdf_name}
    pdf_retrieval = kg_retrieval_chain(PDFAGENTPROMPTTEMPLATE_B, input_variables)
    pdf_retrieval_answer = await convert_to_dict(pdf_retrieval["answer"])

    answer = pdf_retrieval_answer["response"]
    pdf_data_points = pdf_retrieval_answer["data_points"]
    relevant_columns = pdf_retrieval_answer["relevant_columns"]

    # Get data from table by comparing pdf data points with levenshtein distance of values in table
    ranked_results_via_ld = levenshtein_dist_from_db(table_name, pdf_data_points)

    relevant_columns_from_pdf = [col.strip() for col in relevant_columns.split(",")]
    validated_data_points_via_ld = []

    for col in relevant_columns_from_pdf:
        for data in ranked_results_via_ld:
            if data[0] == col:
                data_str = "( Column Name: " + str(data[0]) + ", Value: " + str(data[1]) + " )"
                validated_data_points_via_ld.append(data_str)

    validated_data_points_via_ld = ", ".join(str(element) for element in validated_data_points_via_ld[:10])

    inputs = {
        "question": question,
        "pdf_data": answer,
        "table_data": validated_data_points_via_ld
    }

    # Augment question with data points from table
    parsed_result = await json_parser_prompt_chain_data_analyst(inputs)

    if parsed_result["next_agent"] == "human_input":
        rprint("Interupt in Data Analyst Node")
        return Command(goto="human_input", state=state)
    else:
        state["next_agent"] = parsed_result["next_agent"]
        state["is_multiagent"] = True
        state["augmented_question"] = parsed_result["augmented_question"]
        state["table_relevant_data"] = validated_data_points_via_ld
        state["pdf_relevant_data"] = pdf_data_points
        return state


async def human_input(state: MessageState):
    """Human Input Node to get user input and communicate with Data Analyst"""
    human_message = interrupt("human_input")

    state["messages"].append(HumanMessage(content=human_message))
    state["next_agent"] = "sql_agent"

    return state
