# Recommended Enhancements
# Handle Missing Keys

# Replace all direct indexing of time_table[str(...)] with time_table.get(str(...), 0) or something similar.
# Remove Duplicate handle_on_chat_model_stream

# You have two definitions. The first is overshadowed by the second that includes time_table. Remove the first if it’s not used.
# Initialize next_agent and time_table

# In run_chatbots, define next_agent = None and time_table = {} near the top so that you don’t reference them before assignment.
# If you rely on time_table, store an initial time for each agent if needed or rely on a .get(..., time.time()) fallback.
# Refine Interrupt Logic (Optional)

# Currently, if multiple interrupts queue up quickly, you only handle them one at a time. That might be acceptable, but if you want the user to be able to spam interrupts, you may want to handle them differently.
# Remove or Replace Blank Messages

# You send "" for start_next_agent_stream(...) with an empty string. If you don’t want a blank message in the UI, consider replacing with a “Thinking…” placeholder or removing it if not needed.
# Consolidate Logging

# You have a mix of logging.debug(...) and rprint(...). That’s fine for debugging, but in a production environment, you might want all logs to go through a consistent logging approach.
# Docstrings

# Most handlers have docstrings. Great. The main run_chatbots function also has a docstring, but you can further detail how interrupt logic works, what time_table is for, etc.


import os
import time
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
import logging
from rich import print as rprint
from config import LoadPostgresConfig
from llm_core.src.llm.langgraph_graph_api import workflow
from llm_core.src.llm.agents import *
from llm_core.src.utils.utility_function import *
from llm_core.src.utils.chatbot_manager import ChatbotManager
from llm_core.src.llm.input_layer import message_queue, start_chat_state
from llm_core.src.llm.output_layer import start_next_agent_stream, char_agent_stream, end_agent_stream, usage_agent_stream, query_agent_stream
from models.models import MessageInstance
from llm_core.src.llm.function_layer import sql_agent_function
from typing import Tuple, List

# Set up tracing for debugging
os.environ["LANGCHAIN_TRACING_V2"] = "true"

db = LoadPostgresConfig()

tasks = {}
active_websockets = {}
active_chatbots = {}


memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
manager = ChatbotManager()



async def run_chatbots( session_id: str):
    chatbot = await manager.get_chatbot(session_id)
    config = chatbot["config"]

    while True:

        try:
            # Wait for a new message (blocking until available)
            message = await message_queue.get()
            logging.debug(f"Processing message: {message}, Queue size: {message_queue.qsize()}")


            state = await start_chat_state(manager, session_id, message)
            # rprint("Starting state: ", state["messages"])

            thread_id = config['configurable']['thread_id']
            # rprint("Thread ID: ", thread_id)
            # rprint("Config: ", config)
            # rprint("app state: ", app.get_state(config=config))

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
                # Human-in-loop flag
                if is_interrupted:
                    message = await message_queue.get()
                    
                    holder_message = await start_next_agent_stream(manager, session_id, "", next_agent, 0)
                    holder_message = MessageInstance(**holder_message)
                    await safe_send(active_websockets, holder_message, session_id)
                    
                    logging.debug(f"Processing message: {message}, Queue size: {message_queue.qsize()}")
                    input_arg = Command(resume=message.message)

                async for event in app.astream_events(input_arg, config, version="v2"):
                    if event["event"] == "on_chain_start":
                        # if "run_id" in event:
                        #     rprint("on_chain_start: ", event["run_id"], cur_agent)
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
                            # rprint("on_chat_model_end: ", event["run_id"], cur_agent)
                            tool_call_name = ""
                            if "tool_calls" in event["data"]["output"].additional_kwargs:
                                tool_call_name = event["data"]["output"].additional_kwargs["tool_calls"][0]["function"]["name"]

                            model_name = event["data"]["output"].response_metadata["model_name"]
                            input_tokens = event["data"]["output"].usage_metadata["input_tokens"]
                            output_tokens = event["data"]["output"].usage_metadata["output_tokens"]
                            total_tokens = event["data"]["output"].usage_metadata["total_tokens"]
                            run_id = event["run_id"]
                            tokens = [input_tokens, output_tokens, total_tokens, run_id, tool_call_name, model_name]
                            # rprint("Tokens: ", tokens)

                            await handle_on_chat_model_end(event, manager, session_id, active_websockets, tokens, cur_agent)

                    if event["event"] == "on_chain_end" and not is_interrupted:
                        # if "run_id" in event:
                        #     rprint("on_chain_end: ", event["run_id"], cur_agent)
                        traversing_graph = await handle_on_chain_end(event, 
                            manager, 
                            session_id, 
                            active_websockets, 
                            time_table, 
                            traversing_graph)
                        
                        if not traversing_graph:
                            break

                    # rprint("interrupts: ", interrupts.tasks)

                    interrupts = app.get_state(config)
                    if not is_interrupted:
                        for t in interrupts.tasks:
                            if t.interrupts:
                                is_interrupted = True
                                rprint("Interrupted!")
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
                print(f"Task for session_id {session_id} removed")


async def handle_on_chat_model_end(event: dict, 
                                   manager, 
                                   session_id: str, 
                                   active_websockets: dict, 
                                   usage_metadata, role) -> tuple[str, str]:
    """
    Handle the 'on_chat_model_end' event
    """
    end_time = time.time()
    current_time = end_time - time_table.get(str(role), 0)
    message = await usage_agent_stream(manager, session_id, usage_metadata, role, current_time)
    message = MessageInstance(**message)
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
                    start_time = (time_table[str(next_agent)])
                    holder_message = await start_next_agent_stream(manager, session_id, "", next_agent, start_time, thread_id)
                    holder_message = MessageInstance(**holder_message)
                    await safe_send(active_websockets, holder_message, session_id)
                    return cur_agent, next_agent
            
            if "has_function_call" in input_data:
                role = input_data['current_agent']
                end_time = time.time()
                if input_data["function_call"] == "sql_query":
                    # rprint("Query: ", input_data['answer_query'])
                    # rprint("Table: ", input_data['table_name'], "Query: ", input_data['answer_query'],"role: ", role)
                    message_str = sql_agent_function(table_name=input_data['table_name'], query=input_data['answer_query'], role=role)
                    rprint("message_str: ", message_str)
                    finish_time = (end_time - time_table[str(role)])
                    if "Result" in message_str:
                        end_message = await end_agent_stream(manager, session_id, message_str["Result"], role, finish_time, str(input_data['visualizing_query']), str(input_data['viewing_query_label']))
                        end_message = MessageInstance(**end_message)
                        await safe_send(active_websockets, end_message, session_id)
                        time_table[str(role)] = 0
                    elif "Error" in message_str:
                        end_message = await end_agent_stream(manager, session_id, message_str["Error"] + ", while executing " + str(input_data['answer_query']), role, finish_time, None, None)
                        end_message = MessageInstance(**end_message)
                        # rprint("end_message: ", end_message)
                        await safe_send(active_websockets, end_message, session_id)
                        time_table[str(role)] = 0
                if input_data["function_call"] == "sql_manipulator_query":
                    finish_time = (end_time - time_table[str(role)])
                    end_message = await query_agent_stream(manager, session_id, input_data['answer_query'], role, finish_time, str(input_data['answer_query']), str(input_data['viewing_query_label']))
                    end_message = MessageInstance(**end_message)
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
    # if len(event['data'].keys()) > 1:
    #     rprint("handle_on_chat_model_stream event key: ", event['data'].keys())
    
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
    event: dict,
    manager,
    session_id: str,
    active_websockets: dict,
    time_table: dict,
    traversing_graph: bool
):
    global app
    if "output" in event['data'] and isinstance(event['data']['output'], dict):
        # keys = event['data']['output'].keys()
        # rprint("handle_on_chain_end OUTPUT keys: ", keys)
        if type(event['data']['output']) == dict and 'next_agent' in event['data']['output']:
            time_table[str(event['data']['output']['current_agent'])] = 0
            if event['data']['output']['next_agent'] == "__end__":
                traversing_graph = False
                # chatbot = await manager.get_chatbot(session_id)
                # config = chatbot["config"]
                # rprint("event['data']['output']['messagess']: ", event['data']['output']['messages'][-1])
                # app.update_state(
                #     config=config,
                #     values={"messages": event["data"]["output"]["messages"]},
                # )
     
                # rprint("app state: ", app_state)
                # rprint("app state: ", app.get_state(config=config))

    return traversing_graph