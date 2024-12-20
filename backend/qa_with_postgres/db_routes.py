from fastapi import APIRouter, HTTPException, File, UploadFile, Request, BackgroundTasks, WebSocket, WebSocketDisconnect
import shutil
import psycopg2
import pandas as pd
import re
from qa_with_postgres.db_connect import get_db_connection
from qa_with_postgres.file_config import UPLOAD_DIR
from qa_with_postgres.models import TableNameRequest, TableSummaryDataRequest
from qa_with_postgres.db_utility import ingest_file, fetch_and_process_rows_with_embeddings, get_table_data, get_summary_data, get_table_size, if_table_exists, get_assistant_id, get_vector_store_id, remove_thread_id, add_thread_id, get_thread_id
from qa_with_postgres.table_tasks import add_table, get_tasks_for_table, add_task, update_task, get_task, delete_task_table
from qa_with_postgres.assistants_stream import EventHandler
from qa_with_postgres.assistants import client

# from qa_with_postgres.chatbot import ChatBot
import requests
import httpx
import asyncio
from typing import List, Dict
import uuid
import json
import os

# Create a router object
router = APIRouter()

@router.post("/upload", status_code=200)
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None
):
    print("Uploading file...")
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    table_name = re.sub(r'\.csv$', '', file.filename)

    try:
        # Ingest the file into the database
        ingest_file(file_location, table_name)

        # summary_table_exists = await if_table_exists(table_name + "_summary")

        # if summary_table_exists:
        #     return
        
        # await fetch_and_process_rows_with_embeddings(table_name)
        # summary_data = await get_summary_data(table_name=table_name.lower() + "_summary")
        
        # random_values_json = summary_data["repacked_rows"]
        # ordered_values_json = summary_data["row_numbered_json"]

        task_id = str(uuid.uuid4())

        add_table(table_name.lower())


        # add_task(table_name.lower(), task_id, "SummarizeColumns")
        # update_task(table_name.lower(), task_id, "Started", None)
        # task = get_task(table_name.lower(), task_id)

        # table_name_data = {"task_id": task_id, "table_name": table_name.lower(), "random_values_json": random_values_json, "ordered_values_json": ordered_values_json}
         
        # Send to crew AI
        # async with httpx.AsyncClient() as client:
        #     # Post to the analyze endpoint
        #     analyze_url = f"http://127.0.0.1:5000/tables/{table_name.lower()}/analyze"
        #     analyze_response = await client.post(analyze_url, json=table_name_data)

        #     if analyze_response.status_code != 200:
        #         raise HTTPException(status_code=500, detail="Failed to analyze table")

        # return {"task": task}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    



    

@router.delete("/delete-table", status_code=204)
async def delete_table(table: TableNameRequest , request: Request):
    table_name = table.table_name

    delete_task_table(table_name)
    # await request.app.state.assistants.delete_assistant(table_name)
    # await request.app.state.assistants.delete_vector(table_name)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
        # cur.execute(f"DROP TABLE IF EXISTS {table_name}_summary")
        # conn.commit()
        cur.close()
        conn.close()
        return 
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete table")


@router.get("/get-tables", status_code=200)
async def get_files(request: Request):
    try:
        print("Fetching tables...")
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT c.relname AS table_name
            FROM pg_class c
            JOIN pg_description d ON c.oid = d.objoid
            WHERE c.relkind = 'r'  -- 'r' stands for ordinary table
            AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            AND d.description = 'frontend table';
        """)
        files = [row[0] for row in cur.fetchall()]

        print("Tables fetched successfully.")

        cur.close()
        conn.close()

        for file in files:
            result = await load_assistant_id(file, request)

        return files
    
    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching tables.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.post("/get-table", status_code=200)
async def get_table(table: TableNameRequest, request: Request):
    table_name = table.table_name
    page = table.page
    page_size = table.page_size
    
    try:
        table_data = get_table_data(table_name, page, page_size)
        return table_data
    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching table data.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.post("/load-assistant", status_code=200)
async def get_table(table: dict, request: Request):

    table_name = table["table_name"]

    try:
        assistant = await request.app.state.assistants.retrieve_assistant(table_name)
        vector = await request.app.state.assistants.retrieve_vector(table_name)
        thread = await request.app.state.assistants.retrieve_thread(table_name)


        try:
            print("Retrieving conversation")
        except Exception as e:
            print(f"Error retrieving conversation: {str(e)}")

        return {"assistant": assistant, "vector": vector, "thread": thread, "messages": messages}

    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching table data.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
@router.post("/reinitiate-thread", status_code=200)
async def reintiate_thread(table: dict, request: Request):
    table_name = table["table_name"]
    try:
        await request.app.state.assistants.delete_thread(table_name)
        await request.app.state.assistants.create_thread(table_name)
        await load_assistant_id(table_name, request)

        
        return {"status": "success"}
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@router.post("/chat")
async def chat(request: Request):
    data = await request.json()
    message = data.get('message')
    question = message.get('question')
    table_name = message.get('table')

    # await kickoff(question, table_name)

    # # Assuming you're not maintaining conversation history per session
    # conversation = []
    # _, updated_conversation = chatbot_instance.respond(conversation, message)
    # response = updated_conversation[-1][1]
    # response = "hello"

    return {"response": "response"}


@router.get("/status/{table_name}/{task_id}")
async def get_status(table_name: str, task_id: str):
    return get_task(table_name, task_id)



@router.post("/results/{table_name}")
async def receive_results(table_name: str, result: Dict, request: Request):
    print("Received results:", result)
    clean_result = result["result"]
    clean_result = clean_result.strip("```python").strip("```")
    clean_result = json.loads(clean_result)
    clean_result = clean_result["result"]

    task = get_task(table_name, result["task_id"])

    if task and task["description"] == "SummarizeColumns" and result["status"] == "Completed":
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
                f"""
                INSERT INTO {table_name}_summary (id, results)
                VALUES (1, %s)
                ON CONFLICT (id)
                DO UPDATE SET results = EXCLUDED.results;
                """,
                (json.dumps(clean_result),)
            )
        conn.commit()
        cur.close()
        conn.close()
        print("Task completed:", task)
        table_size = await get_table_size(table_name)
        total_sample_row_size = await get_summary_data(table_name + "_summary")
        total_sample_row_size = len(total_sample_row_size["row_numbered_json"])
        await add_assistant_setting(table_name, clean_result, table_size, total_sample_row_size, request)


    update_task(table_name, result["task_id"], result["status"], result["result"])
    return {"status": "success"}


async def add_assistant_setting(table_name, summary_data, table_size, total_sample_row_size, request):
    print("Adding assistant and vector...")

    # Prepare table summary data
    table_summary_data = TableSummaryDataRequest(
        table_name=table_name,
        total_table_row_size=table_size,
        total_sample_row_size=total_sample_row_size,
        results=summary_data,
    )

    print(table_summary_data)
    # Create the summary file
    create_summary_file(table_name, table_summary_data)

    # Handle assistant and vector
    await handle_assistant_and_vector(table_name, request)


async def handle_assistant_and_vector(table_name, request):
    find_assistant = await get_assistant_id(table_name)
    find_vector = await get_vector_store_id(table_name)

    if find_assistant[0] is None and find_vector[0] is None:
        await request.app.state.assistants.add_assistant_setting(table_name)
    else:
        print(f"Assistant for table {table_name} already exists in memory.")


def create_summary_file(table_name, table_summary_data):
    summary_file_name = f"{table_name.lower()}_summary.txt"
    summary_file_path = os.path.join("qa_with_postgres/summary_files", summary_file_name)

    # Ensure the summary_files directory exists
    if not os.path.exists("qa_with_postgres/summary_files"):
        os.makedirs("qa_with_postgres/summary_files")  # Create the folder if it doesn't exist

    # Write the summary to a file if it doesn't exist
    if not os.path.isfile(summary_file_path):
        with open(summary_file_path, "w", encoding="utf-8") as file:
            # Serialize the table_summary_data object to JSON
            file.write(json.dumps(table_summary_data.dict(), indent=4))
    else:
        print(f"Summary file already exists: {summary_file_path}")

    return summary_file_path


async def load_assistant_id(table_name, request):  
    find_assistant = await request.app.state.assistants.load_assistant_id(table_name)

    if find_assistant is None:
        print(f"Assistant for table {table_name} does not exist.")


# You can remove your custom ping/pong implementation.
# @router.websocket("/ws/chat-client")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     print("WebSocket connection open")
#     try:
#         while True:
#             data = await websocket.receive_json()
#             print(f"Chat message received: {data}")
            
#             await websocket.send_json(data)
#     except WebSocketDisconnect as e:
#         print(f"WebSocket disconnected: {e}")


@router.websocket("/ws/chat-client")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection open")
    try:
        while True:
            data = await websocket.receive_json()
            assistant = await get_assistant_id(data["table_name"])
            vector = await get_vector_store_id(data["table_name"])
            thread = await get_thread_id(data["table_name"])

            print(f"Chat message received: {data}")
            print(f"Assistant: {assistant}")
            print(f"Vector: {vector}")
            print(f"Thread: {thread}")

            print(data["message"])

            # Use the EventHandler with the WebSocket
            event_handler = EventHandler(websocket, data["table_name"])

            # Start the stream
            async with client.beta.threads.runs.stream(
                thread_id=thread[0],
                assistant_id=assistant[0],
                model = "gpt-4",
                truncation_strategy = {
                    "type": "last_messages",
                    "last_messages": 2
                },
                instructions=data["message"],
                event_handler=event_handler,
                additional_instructions = f"Answer the question using data from {vector[0]} vector database.",

            ) as stream:
                async for event in stream:
                    if event.event == "thread.message.in_progress":
                        data = {"role": "assistant", "table_name": data["table_name"], "event": "in_progress" , "message": ""}
                        await websocket.send_json(data)

                    if event.event == "thread.message.completed":
                        thread_data = client.beta.threads.messages.list(thread_id=thread[0])
                        # print("")
                        # async for message in thread_data:
                        #     print(message)

                    # if event.event == "thread.message.delta" and event.data.delta.content:
                    #     print("thread.message.delta: ", event.data.delta.content[0].text)
                await stream.until_done()

    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected: {e}")



async def fetch_messages(thread_id):
    try:
        # Fetch messages using the paginator
        paginator = client.beta.threads.messages.list(thread_id=thread_id)

        # async for message in paginator:
        #     # Access the attributes of the message object
        #     print(f"Message from {message.role}: {message.content}")

        result = ""
        val = 0

        async for message in client.beta.threads.messages.list(thread_id=thread_id):

            for content_block in message.content:
                if content_block.type == "text":
                    val += 1
                    print(content_block.text.value, val )
                    return content_block.text.value


    except Exception as e:
        print("Failed to fetch messages:", e)



