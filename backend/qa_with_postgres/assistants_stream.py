from typing_extensions import override
from openai import AsyncAssistantEventHandler
from qa_with_postgres.assistants import client
 
# First, we create a EventHandler class to define
# how we want to handle the events in the response stream.
 
class EventHandler(AsyncAssistantEventHandler):
  def __init__(self, websocket, table_name):
    super().__init__()  # Properly initialize the base class
    self.websocket = websocket
    self.table_name = table_name


  @override
  async def on_text_created(self, text) -> None:
    print(f"\nassistant > ", end="", flush=True)
    data = {"role": "assistant", "table_name": self.table_name, "event": "created" , "message": ""}
    await self.websocket.send_json(data)
      
  @override
  async def on_text_delta(self, delta, snapshot):
    print(delta.value, end="", flush=True)
    data = {"role": "assistant", "table_name": self.table_name, "event": "delta" , "message": delta.value}
    await self.websocket.send_json(data)

      
  async def on_tool_call_created(self, tool_call):
    print(f"\nassistant > {tool_call.type}\n", flush=True)
  
  async def on_tool_call_delta(self, delta, snapshot):
    if delta.type == 'code_interpreter':
      if delta.code_interpreter.input:
        print(delta.code_interpreter.input, end="", flush=True)
      if delta.code_interpreter.outputs:
        print(f"\n\noutput >", flush=True)
        for output in delta.code_interpreter.outputs:
          if output.type == "logs":
            print(f"\n{output.logs}", flush=True)

    # if delta.type == 'file_search':
    #   print(f"\n\noutput >", flush=True)
    #   for output in delta.file_search.outputs:
    #     if output.type == "logs":
    #       print(f"\n{output.logs}", flush=True)

