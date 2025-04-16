import os
import time
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
import logging
from rich import print as rprint
from config import LoadPostgresConfig
from llm_core.src.llm.langgraph_graph_api import workflow_sql, workflow_pdf, workflow_multi
from llm_core.src.llm.agents import *
from llm_core.src.llm_utils.utility_function import *
from llm_core.src.llm_utils.chatbot_manager import ChatbotManager
from llm_core.src.llm.input_layer import  set_chat_state
from llm_core.src.llm.output_layer import start_next_agent_stream, char_agent_stream, end_agent_stream, usage_agent_stream, query_agent_stream
from models.models import MessageInstance
from typing import Tuple, List
import asyncio

# Set up tracing for debugging
os.environ["LANGCHAIN_TRACING_V2"] = "true"

db = LoadPostgresConfig()

tasks = {}
active_websockets = {}
app = None
memory = MemorySaver()
manager = ChatbotManager()
message_queue = asyncio.Queue()



async def run_chatbots(session_id: str):
    global app
    chatbot = await manager.get_chatbot(session_id)
    config = chatbot["config"]
    thread_id = config['configurable']['thread_id']
    chat_state = chatbot["messages"]
    user_selected_component = None

    while True:
        try:
            # Wait for a new message (blocking until available)
            message = await message_queue.get()

            if message.table_name and not message.pdf_name:
                user_selected_component = "sql"
                app = workflow_sql.compile(checkpointer=memory)
                if chat_state[thread_id][message.table_name] == None:
                    state = await set_chat_state(manager, session_id, message)
                    state["next_agent"] = "sql_agent"
                    chat_state[thread_id][message.table_name] = state
                else:
                    state = chat_state[thread_id][message.table_name]
                    state["question"] = HumanMessage(content=message.message)
                    state["messages"].append(HumanMessage(content=message.message))
            
            elif message.pdf_name and not message.table_name:
                user_selected_component = "pdf"
                app = workflow_pdf.compile(checkpointer=memory)
                if chat_state[thread_id][message.pdf_name] == None:
                    state = await set_chat_state(manager, session_id, message)
                    state["next_agent"] = "pdf_agent"
                    chat_state[thread_id][message.pdf_name] = state
                else:
                    state = chat_state[thread_id][message.pdf_name]
                    state["question"] = HumanMessage(content=message.message)
                    state["messages"].append(HumanMessage(content=message.message))
            
            elif message.table_name and message.pdf_name:
                user_selected_component = "multi"
                app = workflow_multi.compile(checkpointer=memory)
                state = await set_chat_state(manager, session_id, message)
                state["next_agent"] = "data_analyst"
                state["is_multiagent"] = True

            is_interrupted = False
            traversing_graph = True
            cur_agent = None
        
            words_to_find = ['<_START_>', '<_']
            word_buffer = ""
            word_state = False
            str_response = []
            char_backlog = []
            input_arg = state
        

            while traversing_graph:
                if is_interrupted:
                    message = await message_queue.get()
                    rprint("Processing interrupted message: ", message)
                    holder_message = await start_next_agent_stream(manager, session_id, "", next_agent, 0, thread_id)
                    holder_message = MessageInstance(**holder_message)
                    await safe_send(active_websockets, holder_message, session_id)
                    
                    logging.debug(f"Processing message: {message}, Queue size: {message_queue.qsize()}")
                    input_arg = Command(resume=message.message)

                async for event in app.astream_events(input_arg, config, version="v2"):
                    if event["event"] == "on_chain_start":
                        cur_agent, next_agent = await handle_on_chain_start(
                            event, 
                            manager, 
                            session_id, 
                            cur_agent, 
                            time_table, 
                            active_websockets,
                            thread_id)

                    if event["event"] == "on_chat_model_stream":

                        word_buffer, word_state, str_response, char_backlog = await handle_on_chat_model_stream(
                            event,
                            manager,
                            session_id,
                            active_websockets,
                            words_to_find,
                            word_buffer,
                            word_state,
                            str_response,
                            char_backlog,
                            time_table
                        )
                        
                    if event["event"] == "on_chat_model_end":
                        if "run_id" in event:
                            tool_call_name = ""
                            if "tool_calls" in event["data"]["output"].additional_kwargs:
                                tool_call_name = event["data"]["output"].additional_kwargs["tool_calls"][0]["function"]["name"]

                            model_name = event["data"]["output"].response_metadata["model_name"]
                            input_tokens = event["data"]["output"].usage_metadata["input_tokens"]
                            output_tokens = event["data"]["output"].usage_metadata["output_tokens"]
                            total_tokens = event["data"]["output"].usage_metadata["total_tokens"]
                            run_id = event["run_id"]
                            tokens = [input_tokens, output_tokens, total_tokens, run_id, tool_call_name, model_name]

                            await handle_on_chat_model_end(event, manager, session_id, active_websockets, tokens, cur_agent)

                    if event["event"] == "on_chain_end" and not is_interrupted:
                        traversing_graph, end_state = await handle_on_chain_end(config, event, 
                            manager, 
                            session_id, 
                            active_websockets, 
                            time_table, 
                            traversing_graph)
                        if end_state and user_selected_component == "sql":
                            last_message = end_state["messages"][-1]
                            chat_state[thread_id][message.table_name]["messages"].append(last_message)
                        if not traversing_graph:
                            break

                    interrupts = app.get_state(config)
                    if not is_interrupted:
                        for t in interrupts.tasks:
                            if t.interrupts:
                                is_interrupted = True
                                # if is_interrupted and user_selected_component == "sql":
                                #     rprint("Interrupted!")
                                break
                    else:
                        if len(interrupts.tasks) == 0:
                            is_interrupted = False


        except Exception as e:
            logging.error(f"Error in chatbot processing: {e}")
            break
        finally:
            if session_id in tasks:
                del tasks[session_id]
                # rprint("State: ", chat_state[thread_id])

                print(f"Task for session_id {session_id} removed")


async def handle_on_chat_model_end(event: dict, 
                                   manager, 
                                   session_id: str, 
                                   active_websockets: dict, 
                                   usage_metadata, role) -> tuple[str, str]:
    """
    Handle the 'on_chat_model_end' event
    """
    # rprint("handle_on_chat_model_end: ", event)
    end_time = time.time()
    current_time = end_time - time_table.get(str(role), 0)
    message = await usage_agent_stream(manager, session_id, usage_metadata, role, current_time)
    message = MessageInstance(**message)
    # rprint("message: ", message)
    await safe_send(active_websockets, message, session_id)


async def handle_on_chain_start(
    event: dict,
    manager,
    session_id: str,
    cur_agent: str,
    time_table: dict,
    active_websockets: dict,
    thread_id: str
) -> tuple[str, str]:
    """
    Handle the 'on_chain_start' event. Return updated (cur_agent, next_agent).
    """
    next_agent = None
    data = event.get("data", {})     
    if isinstance(data, dict) and "input" in data:
        input_data = data["input"]
        if isinstance(input_data, dict) and "next_agent" in input_data:
            # rprint("handle_on_chain_start INPUT: ", input_data)
            next_agent = input_data["next_agent"]
            if cur_agent != next_agent and "has_function_call" not in input_data:
                cur_agent = next_agent
                if cur_agent != "__end__":
                    # rprint("Condition 1")
                    start_time = (time_table[str(next_agent)])
                    # rprint("handle_on_chain_start: ", cur_agent, next_agent, thread_id)
                    holder_message = await start_next_agent_stream(manager, session_id, "", next_agent, start_time, thread_id)
                    holder_message = MessageInstance(**holder_message)
                    await safe_send(active_websockets, holder_message, session_id)
                    return cur_agent, next_agent
            
            if "has_function_call" in input_data:
                role = input_data['current_agent']
                query_type = input_data['query_type']
                end_time = time.time()
                # rprint("input_data: ", input_data)
                if input_data["query_type"] == "retrieval":
                    finish_time = (end_time - time_table[str(role)])
                    # rprint("Table: ", input_data['table_name'], "Query: ", input_data['answer_retrieval_query'],"role: ", role)
                    if input_data['query_failed'] is False:
                        # rprint("Condition 2")
                        message_str = sql_agent_function(table_name=input_data['table_name'], query=input_data['answer_retrieval_query'], role=role, query_type=query_type)
                        end_message = await query_agent_stream(manager, 
                                                               session_id, 
                                                               " <br><br> Query: " + input_data['answer_retrieval_query'] + "<br><br> Query Result: <br>" + message_str["Result"], 
                                                               role, 
                                                               finish_time, 
                                                               str(input_data['visualize_retrieval_query']), 
                                                               str(input_data['visualize_retrieval_label']),
                                                               str(query_type))
                        end_message = MessageInstance(**end_message)
                        # rprint("end_message handle_on_chain_start: ", end_message)
                        await safe_send(active_websockets, end_message, session_id)
                        time_table[str(role)] = 0
                    else:

                        end_message = await query_agent_stream(manager, 
                                                               session_id,
                                                               " <br><br> Query: " + str(input_data['answer_retrieval_query']), 
                                                               role, 
                                                               finish_time, 
                                                               None, 
                                                               None,
                                                               str(query_type))
                        end_message = MessageInstance(**end_message)
                        await safe_send(active_websockets, end_message, session_id)
                        time_table[str(role)] = 0
                if input_data["query_type"] == "manipulation":
                    finish_time = (end_time - time_table[str(role)])
                    end_message = await query_agent_stream(manager, session_id, " <br><br> Query: " + input_data['perform_manipulation_query'], role, finish_time, str(input_data['perform_manipulation_query']), str(input_data['perform_manipulation_label']), str(query_type))
                    end_message = MessageInstance(**end_message)
                    # rprint("end_message handle_on_chain_start: ", end_message)
                    await safe_send(active_websockets, end_message, session_id)
    return cur_agent, next_agent



async def handle_on_chat_model_stream(
    event: dict,
    manager,
    session_id: str,
    active_websockets,
    words_to_find: List[str],
    word_buffer: str,
    word_state: bool,
    str_response: List[str],
    char_backlog: List[str],
    time_table: dict
    
) -> Tuple[str, bool, List[str], List[str]]:
    
    prev_char_backlog = char_backlog.copy()

    word_buffer, word_state, str_response, char_backlog = process_stream_event(
        event, words_to_find, word_buffer, word_state, str_response, char_backlog
    )
    
    if word_state and len(str_response) > 0 and prev_char_backlog == char_backlog:
        role = event['metadata']['langgraph_node']
        end_time = time.time()
        current_time = end_time - time_table.get(str(role), 0)
        message = await char_agent_stream(manager, session_id, word_buffer, role, current_time)
        message = MessageInstance(**message)
        await safe_send(active_websockets, message, session_id)

    return word_buffer, word_state, str_response, char_backlog


async def handle_on_chain_end(
    config,
    event: dict,
    manager,
    session_id: str,
    active_websockets: dict,
    time_table: dict,
    traversing_graph: bool
):
    global app
    end_state = None
    if "output" in event['data'] and isinstance(event['data']['output'], dict):
        # keys = event['data']['output'].keys()
        # rprint("handle_on_chain_end OUTPUT keys: ", keys)
        if type(event['data']['output']) == dict and 'next_agent' in event['data']['output']:
            time_table[str(event['data']['output']['current_agent'])] = 0
            if event['data']['output']['next_agent'] == "__end__":
                traversing_graph = False
                end_state = event['data']['output']

    return traversing_graph, end_state