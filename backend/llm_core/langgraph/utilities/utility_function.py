import logging
from rich import print as rprint
from llm_core.langgraph.models.models import MessageState, MessageInstance
import openai
from langchain_core.messages import AIMessage
from rich import print as rprint
import json
import re


async def convert_to_dict(string: str) -> dict:
    """convers a json string to a dictionary"""
    match = re.search(r'```json\s*(\{.*?\})\s*```', string, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        json_str = string.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("JSON parsing error:", e)
        return {}


async def set_state(state: MessageState, response: dict) -> MessageState:
    for key, value in response.items():
        if key == "answer":
            answer = AIMessage(content=value)
            state["answer"] = answer
            state["messages"].append(answer)
        else:
            state[key] = value
    return state


def find_word_in_text( word, words_to_find, word_buffer):
    for word_to_find in words_to_find:
        if word_to_find in word_buffer:
            return [True, word_to_find]
    return [False, None]

def update_word_state(find_word, words_to_find, word_buffer, word_state):
    """Update the word state based on the matched word."""
    if find_word in ["<_START_>"]:
        return True, ""
    elif find_word in ["<_", "```"] and word_state and word_buffer:
        return False, word_buffer
    return word_state, word_buffer


def process_response(word, str_response, char_backlog):
    """Process the response string and handle backlog characters."""
    str_response.append(word)

    if len(str_response) == 1 and str_response[0] == ">":
        str_response.pop(0)

    if str_response and str_response[-1].strip() == "<":
        char_backlog.append(str_response.pop())
    else:
        if char_backlog:
            char_backlog.append(str_response.pop() if str_response else "")
        else:
            pass

    if len(char_backlog) > 1:
        char_backlog.clear()

    return str_response, char_backlog


def handle_finish_reason(event, word_state, char_backlog):
    """Handle the finish reason and reset states if needed."""
    if 'finish_reason' in event["data"]['chunk'].response_metadata:
        reason = event["data"]['chunk'].response_metadata['finish_reason']
        if reason == "stop":
            return False, []
    return word_state, char_backlog


def process_stream_event(event, words_to_find, word_buffer, word_state, str_response, char_backlog):
    """Process a single streaming event and update the state."""
    word = event["data"]['chunk'].content

    word_buffer += word

    word_buffer = word_buffer.replace("\\n\\n", "<br/><br/>").replace("\\n", "<br/>")

    find_word = find_word_in_text(word, words_to_find, word_buffer)

    # Update word state
    word_state, word_buffer = update_word_state(find_word[1], words_to_find, word_buffer, word_state)

    if word_state:
        str_response, char_backlog = process_response(word, str_response, char_backlog)
    else:
        str_response = []
        
    word_state, char_backlog = handle_finish_reason(event, word_state, char_backlog)

    return word_buffer, word_state, str_response, char_backlog


async def safe_send(active_websockets, message: MessageInstance, session_id: str):
    try:
        websocket = active_websockets[session_id]
    except KeyError:
        rprint(websocket.client_state)
        logging.warning("Attempted to send a message on a closed WebSocket.")
        return
    
    if websocket.client_state.name == "CONNECTED":
        message = message.model_dump()
        await websocket.send_json(message)
    else:
        rprint(websocket.client_state)
        logging.warning("Attempted to send a message on a closed WebSocket.")




async def start_next_agent_stream(manager, session_id, message_str: str, next_agent: str, time: float, thread_id: str):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
                    "event": "on_chain_start",
                    "message": message_str,
                    "table_name": manager.get_var("table_name"),
                    "pdf_name": manager.get_var("pdf_name"),
                    "role": next_agent,
                    "time": float_time,
                    "thread_id": thread_id
                }
    
    return message


async def char_agent_stream(manager, session_id, word_buffer: str, role: str, time: float):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
            "event": "on_chat_model_stream", 
            "message": word_buffer,
            "table_name": manager.get_var("table_name"),
            "pdf_name": manager.get_var("pdf_name"),
            "role": role,
            "time": float_time,
            }

    return message

async def usage_agent_stream(manager, session_id, usage_metadata: list, role: str, time: float):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
            "event": "on_chat_model_end", 
            "table_name": manager.get_var("table_name"),
            "pdf_name": manager.get_var("pdf_name"),
            "input_tokens": usage_metadata[0],
            "output_tokens": usage_metadata[1],
            "total_tokens": usage_metadata[2],
            "run_id": usage_metadata[3],
            "model_name": usage_metadata[5],
            "tool_call_name": usage_metadata[4],
            "role": role,
            "time": float_time,
            }

    return message


async def query_agent_stream(manager, session_id, message_str: str, role: str, time: float, visualizing_query: str, viewing_query_label: str, query_type: str):
    time_int = int(time * 1000)
    float_time = float(time_int) / 1000
    message = {
            "event": "on_query_stream", 
            "message": message_str,
            "table_name": manager.get_var("table_name"),
            "pdf_name": manager.get_var("pdf_name"),
            "role": role,
            "time": float_time,
            "visualizing_query": visualizing_query,
            "viewing_query_label": viewing_query_label,
            "query_type": query_type
            }

    return message

