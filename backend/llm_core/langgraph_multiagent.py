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
from llm_core.src.llm.output_layer import start_next_agent_stream, char_agent_stream, end_agent_stream
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
                        cur_agent, next_agent = await handle_on_chain_start(
                            event, 
                            manager, 
                            session_id, 
                            cur_agent, 
                            time_table, 
                            active_websockets)

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

                    if event["event"] == "on_chain_end" and not is_interrupted:
                        traversing_graph = await handle_on_chain_end(event, 
                            manager, 
                            session_id, 
                            active_websockets, 
                            time_table, 
                            traversing_graph)
                        
                        if not traversing_graph:
                            break

                    interrupts = app.get_state(config)

                    if len(interrupts.tasks) > 0 and interrupts.tasks[0].interrupts and not is_interrupted:
                        is_interrupted = True
                        break
                    elif len(interrupts.tasks) == 0 and is_interrupted:
                        is_interrupted = False

        except Exception as e:
            logging.error(f"Error in chatbot processing: {e}")
            break
        finally:
            if session_id in tasks:
                del tasks[session_id]
                print(f"Task for session_id {session_id} removed")



async def handle_on_chain_start(
    event: dict,
    manager,
    session_id: str,
    cur_agent: str,
    time_table: dict,
    active_websockets: dict
) -> tuple[str, str]:
    """
    Handle the 'on_chain_start' event. Return updated (cur_agent, next_agent).
    """
    next_agent = None
    data = event.get("data", {})     
    if isinstance(data, dict) and "input" in data:
        input_data = data["input"]
        if isinstance(input_data, dict) and "next_agent" in input_data:
            next_agent = input_data["next_agent"]
            if cur_agent != next_agent:
                cur_agent = next_agent
                if cur_agent != "__end__":
                    start_time = (time_table[str(next_agent)])
                    holder_message = await start_next_agent_stream(manager, session_id, "", next_agent, start_time)
                    holder_message = MessageInstance(**holder_message)
                    await safe_send(active_websockets, holder_message, session_id)
                    return cur_agent, next_agent
    return cur_agent, next_agent


async def handle_on_chat_model_stream(
    event: dict,
    manager,
    session_id: str,
    active_websockets: dict,
    words_to_find: list,
    word_buffer: str,
    word_state: bool,
    str_response: list,
    char_backlog: list
) -> tuple[str, bool, list, list]:
    """
    Handle the 'on_chat_model_stream' event. Return updated (word_buffer, word_state, str_response, char_backlog).
    """
    prev_char_backlog = char_backlog.copy()
    word_buffer, word_state, str_response, char_backlog = process_stream_event(
        event, words_to_find, word_buffer, word_state, str_response, char_backlog
    )
    rprint(word_buffer, word_state, str_response, char_backlog)
    if word_state and len(str_response) > 0 and prev_char_backlog == char_backlog:
        # Send on_chat_model_stream message to client
        role = event['metadata']['langgraph_node']
        end_time = time.time()
        current_time = (end_time - time_table[str(role)])
        message = await char_agent_stream(manager, session_id, word_buffer, role, current_time)
        message = MessageInstance(**message)
        await safe_send(active_websockets, message, session_id)


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
    event: dict,
    manager,
    session_id: str,
    active_websockets: dict,
    time_table: dict,
    traversing_graph: bool
):
    rprint(time_table)
    
    if "output" in event['data'] and isinstance(event['data']['output'], dict):
        rprint(event['data']['output'])
        keys = event['data']['output'].keys()
        if 'has_function_call' in keys and event['data']['output']['has_function_call'] == True:
            role = event['data']['output']['current_agent']
            end_time = time.time()
            if event['data']['output']['function_call'] == "sql_query":
                message_str = sql_agent_function(table_name=event['data']['output']['table_name'], query=event['data']['output']['answer_query'])

                finish_time = (end_time - time_table[str(role)])
                end_message = await end_agent_stream(manager, session_id, message_str, role, finish_time, str(event['data']['output']['answer_query']), str(event['data']['output']['viewing_query_label']))
                end_message = MessageInstance(**end_message)
                await safe_send(active_websockets, end_message, session_id)
                time_table[str(role)] = 0

        if type(event['data']['output']) == dict and 'next_agent' in event['data']['output']:
            time_table[str(event['data']['output']['current_agent'])] = 0
            if event['data']['output']['next_agent'] == "__end__":
                traversing_graph = False

    return traversing_graph