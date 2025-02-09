import logging
from rich import print as rprint
from models.models import MessageInstance


def find_word_in_text( word, words_to_find, word_buffer):
    # print( "input word: ", word )
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


def process_stream_event_type(event):
    if event.get("event") == "on_chain_start":
            data = event.get("data", {})     
            if isinstance(data, dict) and "input" in data:
                input_data = data["input"]
                if isinstance(input_data, dict) and "next_agent" in input_data:
                    next_agent = input_data["next_agent"]
                    return "on_chain_start", next_agent
                
    

    return None, None



    