import openai
from qa_with_postgres.load_config import LoadConfig
import os
import json
import asyncio
from qa_with_postgres.db_utility import add_assistant_setting_to_db, get_assistant_id, get_vector_store_id, get_thread_id, remove_thread_id, add_thread_id

config = LoadConfig()
openai.api_key = config.openai_api_key
client = openai.AsyncOpenAI()


class Assistants:
    def __init__(self):
        self.assistants = {}
        self.vector_stores = {}
        self.threads = {}


    async def load_assistant_id(self, table_name):

        if table_name in self.assistants and self.assistants[table_name] is not None and table_name in self.vector_stores and self.vector_stores[table_name] is not None:
            return True
        
        print(f"Loading assistant for table {table_name}")
        
        assistant_id = await get_assistant_id(table_name)
        vector_store_id = await get_vector_store_id(table_name)
        thread_id = await get_thread_id(table_name)
        

        if assistant_id[0] is not None and vector_store_id[0] is not None and thread_id[0] is not None:
            print(f"Assistant for table {table_name}: {assistant_id[0]}, Vector Store: {vector_store_id[0]}, Thread: {thread_id[0]}")
            print(assistant_id[0])
            self.assistants[table_name] = assistant_id[0]
            self.vector_stores[table_name] = vector_store_id[0]
            self.threads[table_name] = thread_id[0]
            return True

        return False
    
    
    


    async def add_assistant_setting(self, table_name):
        # Verify summary file existence
        summary_file_name = f"{table_name}_summary.txt"
        summary_file_path = os.path.join("qa_with_postgres/summary_files", summary_file_name)

        if not os.path.isfile(summary_file_path):
            print(f"Summary file {summary_file_path} does not exist.")
            return

        # Create a new assistant
        print("Adding new assistant: ", config.openai_model)

        assistant = await client.beta.assistants.create(
            name=f"smarttable Assistant",
            instructions="You verify if the user's question is relevant to the content of the table. Look at the file provided to verify. You never refer to the tools at your disposal",
            model=config.openai_model,
            tools=[{"type": "file_search"}]
        )

        # Create a vector store
        vector_store = await client.beta.vector_stores.create(name=table_name)
        file_streams = [open(summary_file_path, "rb")]

        try:
            file_batch = await client.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id, files=file_streams
            )

            # Update the assistant with vector store
            assistant = await client.beta.assistants.update(
                assistant_id=assistant.id,
                tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
            )

            thread = await client.beta.threads.create()
            
        finally:
            for file_stream in file_streams:
                file_stream.close()
            # if os.path.isfile(summary_file_path):
            #     os.remove(summary_file_path)

        # Update class attributes
        self.assistants[table_name] = assistant.id
        self.vector_stores[table_name] = vector_store.id
        self.threads[table_name] = thread.id


        await add_assistant_setting_to_db(table_name, assistant.id, vector_store.id, thread.id)
       


    async def retrieve_assistant(self, table_name):
        try:
            # await  self.load_assistant_id(table_name)
            assistant = await client.beta.assistants.retrieve(self.assistants[table_name])
            return assistant
        except Exception as e:
            print(f"Error retrieving assistant: {str(e)}")
            return None
    
    async def retrieve_vector(self, table_name):
        try:
            # await self.load_assistant_id(table_name)
            vector = await client.beta.vector_stores.retrieve(self.vector_stores[table_name])
            return vector
        except Exception as e:
            print(f"Error retrieving vector: {str(e)}")
            return None
    
    async def retrieve_thread(self, table_name):
        try:
            # await self.load_assistant_id(table_name)
            print("Retrieving thread", self.threads)
            thread = await client.beta.threads.retrieve(self.threads[table_name])
            return thread
        except Exception as e:
            print(f"Error retrieving thread: {str(e)}")
            return None
    
    async def delete_assistant(self, table_name):
        if table_name not in self.assistants:
            return None
        
        await client.beta.assistants.delete(self.assistants[table_name])
        del self.assistants[table_name]


    async def delete_vector(self, table_name):
        if table_name not in self.vector_stores:
            print(f"Vector store for table {table_name} does not exist.")
            return None
        
        await client.beta.vector_stores.delete(self.vector_stores[table_name])
        del self.vector_stores[table_name]
        print(self.vector_stores)

    async def delete_thread(self, table_name):
        if table_name not in self.threads:
            print(f"Thread for table {table_name} does not exist.")
            return None
        
        try:
            await client.beta.threads.delete(self.threads[table_name])
            del self.threads[table_name]
            await remove_thread_id(table_name)
        except Exception as e:
            print(f"Error deleting thread: {str(e)}")
            return None


    async def create_thread(self, table_name):
        try:
            thread = await client.beta.threads.create()
            await add_thread_id(table_name, thread.id)
            self.threads[table_name] = thread.id
            return thread
        except Exception as e:
            print(f"Error creating thread: {str(e)}")
            return None


# thread.py

class Thread:
    def __init__(self, thread_id, table_name, additional_instructions):
        self.thread_id = thread_id
        self.table_name = table_name
        self.additional_instructions = additional_instructions
        self.messages = []
