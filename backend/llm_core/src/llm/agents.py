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
from db.get_embedding_per_word import process_string_return_similarity
import json
import re
import time
import logging


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
        state["messages"].append(AIMessage(content=response['answer'] + response['answer_retrieval_query']))

        state["answer_retrieval_query"] = response["answer_retrieval_query"]
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
            # rprint("Next Agent: ", state["next_agent"])
            # rprint("Query Type: ", state["query_type"])
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

    # rprint("state['next_agent']: ", state["next_agent"])

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


@tool
def get_weather(location: str):
    """Call to get the weather from a specific location."""
    # This is a placeholder for the actual implementation
    # Don't let the LLM know this though 😊
    if any([city in location.lower() for city in ["sf", "san francisco"]]):
        return "It's sunny in San Francisco, but you better look out if you're a Gemini 😈."
    else:
        return f"I am not sure what the weather is in {location}"

tools = [get_weather]
tools_by_name = {tool.name: tool for tool in tools}


# Define our tool node
async def tool_node(state: MessageState):
    outputs = []
    rprint("Tool Node")
    # rprint("tool call Initial: ", state["messages"])
    for tool_call in state["messages"][-1].tool_calls:
        rprint("tool call: ", tool_call)
        tool_result = await tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
        rprint("tool result: ", tool_result)
        outputs.append(
            ToolMessage(
                content=json.dumps(tool_result),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
        for msg in outputs:
            state["messages"].append(msg)

        rprint("tool call Final: ", outputs)
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

    # rprint("Question: ", question)

    pdf_retrieval = kg_retrieval_chain(question, PDFAGENTPROMPTTEMPLATE_B, state=state)
    rprint("pdf_retrieval: ", type(pdf_retrieval))
    rprint("keys: ", pdf_retrieval.keys())


    pdf_retrieval_answer = pdf_retrieval["answer"]
    # rprint("pdf_retrieval_answer: ", pdf_retrieval_answer)
    pdf_retrieval_source_content = pdf_retrieval["source_documents"][0]

    match = re.search(r'```json\s*(\{.*?\})\s*```', pdf_retrieval_answer, re.DOTALL)
    if match:
        json_str = match.group(1).strip()  # Extract JSON content
        try:
            pdf_retrieval_answer = json.loads(json_str)  # Convert to dict
        except json.JSONDecodeError as e:
            print("JSON parsing error:", e)
            pdf_retrieval_answer = {}

    else:
        # print("No JSON found.")
        try:
            pdf_retrieval_answer = json.loads(pdf_retrieval_answer)  # Convert to dict
        except json.JSONDecodeError as e:
            print("JSON parsing error:", e)
            pdf_retrieval_answer = {}

    # # rprint("pdf_retrieval_answer after clean: ", pdf_retrieval_answer)
    # # rprint("pdf_retrieval_answer after clean type: ", type(pdf_retrieval_answer))
    answer = pdf_retrieval_answer["answer"]
    # # rprint("answer: ", answer)
    data_points = pdf_retrieval_answer["data_points"]
    # # rprint("data_points: ", data_points)
    similar_rows = process_string_return_similarity(data_points, table_name)
    # rprint("similar_rows: ", similar_rows)
    best_line = pdf_retrieval_source_content.metadata["lineNumber"]
    page_number = pdf_retrieval_source_content.metadata["pageNumber"]
    additional_lines = pdf_retrieval_source_content.metadata["additionalLines"]
    # rprint("Additional_Lines: ", str(additional_lines))

    agent_note = answer + "Below is what i found from page number :" + str(page_number) + " take a look around line number: "  + str(best_line) + ". " + "The most relevant data points are: " + str(data_points)
    
    for lines in additional_lines:
        line = "Line Number: " + str(lines["lineNumber"]) + "Text: " + str(lines["text"])
        agent_note += line

    # agent_note = 'Find a good restaurant near NY Aquarium, located at 602 Surf Avenue, Brooklyn, New York 11224, by looking for restaurants in the surrounding area of Coney Island, Brooklyn, especially along Surf Avenue. Consider restaurants with high ratings and a significant number of reviews.'

    agent_scratchpad = AIMessage(content=agent_note)

    # rprint("agent_scratchpad: ", agent_scratchpad)

    inputs = {
        "agent_step": state["agent_step"],
        "agent_scratchpads": agent_scratchpad,
        "question": question,
        "pdf_name": state["pdf_name"],
        "columns_and_types": state["columns_and_types"],
        "table_name": state["table_name"],
    }
    model = "gpt-4o"

    parsed_result = await json_parser_prompt_chain(DATAANALYSTMULTIAGENTPROMPTTEMPLATE, model, inputs)

    if parsed_result["next_agent"] == "human_input":
        rprint("Interupt in Data Analyst Node")
        return Command(goto="human_input", state=state)
    else:
        state["next_agent"] = parsed_result["next_agent"]
        state["is_multiagent"] = True
        state["augmented_question"] = parsed_result["augmented_question"]
        return state




async def should_continue(state: MessageState):
    messages = state["messages"]
    rprint("should_continue: ", messages)

    last_message = messages[-1]
    rprint("Last Message: ", last_message)
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        rprint("No Function Call")
        return "end"
    else:
        rprint("Function Call: ", last_message.tool_calls)
        return "continue"
    
async def human_input(state: MessageState):
    """Human Input Node to get user input and communicate with Data Analyst"""
    rprint("Human Input Node")
    # rprint("human_input State: ", state)

    human_message = interrupt("human_input")

    rprint("Human Message: ", human_message)
    state["messages"].append(HumanMessage(content=human_message))
    state["next_agent"] = "sql_agent"
    state["agent_step"] += 1
    # rprint("Agent Step after human_input: ", state["agent_step"])

    return state

async def cleanup_node(state: MessageState) -> MessageState:
    time_table["cleanup"] = time.time()
    rprint("Cleanup Node Messages: ", state["messages"])
    return state
