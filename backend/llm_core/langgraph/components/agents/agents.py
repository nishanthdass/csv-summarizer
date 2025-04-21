from llm_core.langgraph.models.models import MessageState
from llm_core.langgraph.components.agents.agent_functions import sql_agent_function
from llm_core.langgraph.components.prompts.templates import *
from llm_core.langgraph.components.chains.chains import json_parser_prompt_chain, trimmer, kg_retrieval_chain
from langchain_core.messages import HumanMessage
from rich import print as rprint
from llm_core.langgraph.components.chains.chains import call_sql_agent, json_parser_prompt_augment_question
from langgraph.types import interrupt, Command
from llm_core.langgraph.utilities.utility_function import *
from db.tabular.postgres_utilities import get_all_columns_and_types
from db.tabular.table_operations import levenshtein_dist
from db.tabular.table_embeddings import retrieve_table_embeddings
import time
import logging

# --- Provides response time tracking for each agent ---
time_table = { "sql_agent": 0, "data_analyst": 0, "human_input": 0}


# --- Define Agents ---
async def sql_agent_node(state: MessageState) -> MessageState:
    """SQL Agent takes a question and relevent data points as input and generates a SQL query to answer the question."""
    time_table["sql_agent"] = time.time()
    state["current_agent"] = "sql_agent"

    # Get query type
    try:
        question = state["question"].content
        
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
                answer = state["answer"]
                pdf_data_points = state["pdf_relevant_data"]
                relevant_columns = state["table_relevant_data"]

                # Get data from table by comparing pdf data points with levenshtein distance of values in table
                ranked_results_via_ld = levenshtein_dist(state["table_name"], pdf_data_points)

                # Get data from table by comparing pdf data points with cosine similarity
                ranked_results_via_similarity = retrieve_table_embeddings(state["table_name"], pdf_data_points, k=10)

                relevant_columns_from_pdf = [col.strip() for col in relevant_columns.split(",")]

                table_data_points = {}

                # consolidate data
                for col in relevant_columns_from_pdf:
                    for data in ranked_results_via_ld:
                        # if value is None, make empty array
                        if data[0] == col:
                            if table_data_points.get(col) is None:
                                table_data_points[col] = []
                            table_data_points[col].append(data[1])
                
                for col in relevant_columns_from_pdf:
                    for result in ranked_results_via_similarity:
                        for data in result[0].metadata:
                            if data == col:
                                if table_data_points.get(col) is None:
                                    table_data_points[col] = []
                                table_data_points[col].append(result[0].metadata[data])

                # build a string from the data points
                validated_data_points = ""
                for col in table_data_points:
                    validated_data_points += f"Column Name: {col}, Values: {table_data_points[col]}\n"

                rprint("validated_data_points: ", validated_data_points)

                inputs = {
                    "question": question,
                    "pdf_data": answer,
                    "table_data": validated_data_points,
                }
                rprint("inputs: ", inputs)

                # Augment question with data points from table
                parsed_result = await json_parser_prompt_augment_question(inputs)

                rprint("parsed_result: ", parsed_result)

                if parsed_result: 
                    if parsed_result["next_agent"] == "human_input":
                        rprint("Interupt in Data Analyst Node")
                        return Command(goto="human_input", state=state)

                question = parsed_result["augmented_question"]
                data_points = parsed_result["table_data_points"]
                prompt = await create_sql_multiagent_retrieval_prompt(question, data_points)
                rprint("create_sql_multiagent_retrieval_prompt: ", prompt)

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
      5. Returns the updated state with the retreived information and recommended columns.
    """
    table_name = state["table_name"]

    if not table_name:
        state["is_multiagent"] = False
    else:
        state["is_multiagent"] = True
    pdf_name = state["pdf_name"]
    time_table["data_analyst"] = time.time()
    question = state["question"].content
    if state["is_multiagent"] is False:
        input_variables={"question": question, "pdf_name": pdf_name} # no table_name in 
        pdf_retrieval = kg_retrieval_chain(PDFAGENTPROMPTTEMPLATE_A, input_variables)
        pdf_retrieval_answer = await convert_to_dict(pdf_retrieval["answer"])
        answer = pdf_retrieval_answer["response"]
        pdf_data_points = pdf_retrieval_answer["data_points"]
    else:
        columns = get_all_columns_and_types(table_name)
        col_str = ", ".join(item[0] for item in columns)

        # Get information from PDF KG
        input_variables={"question": question, "columns": col_str, "pdf_name": pdf_name}
        pdf_retrieval = kg_retrieval_chain(PDFAGENTPROMPTTEMPLATE_B, input_variables)
        pdf_retrieval_answer = await convert_to_dict(pdf_retrieval["answer"])
        rprint("pdf_retrieval_answer: ", pdf_retrieval_answer)

        answer = pdf_retrieval_answer["response"]
        pdf_data_points = pdf_retrieval_answer["data_points"]
        relevant_columns = pdf_retrieval_answer["relevant_columns"]
            
    if state["is_multiagent"] is False:
        state["next_agent"]  = "__end__"
        return state
    else:
        state["next_agent"] = "sql_agent"
        state["answer"] = answer
        state["agent_scratchpads"].append(answer)
        state["pdf_relevant_data"] = pdf_data_points
        state["table_relevant_data"] = relevant_columns

        return state


async def human_input(state: MessageState):
    """Human Input Node to get user input and communicate with Data Analyst"""
    human_message = interrupt("human_input")

    state["messages"].append(HumanMessage(content=human_message))
    state["next_agent"] = "sql_agent"

    return state
