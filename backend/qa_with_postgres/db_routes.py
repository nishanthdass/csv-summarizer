from fastapi import APIRouter, HTTPException, File, UploadFile, Request, BackgroundTasks, WebSocket, WebSocketDisconnect
import shutil
import psycopg2
import pandas as pd
import re
from qa_with_postgres.db_connect import get_db_connection
from qa_with_postgres.file_config import UPLOAD_DIR
from qa_with_postgres.models import TableNameRequest
from qa_with_postgres.db_utility import ingest_csv, get_table_data, ingest_pdf
from qa_with_postgres.table_tasks import add_table, get_task, delete_task_table
from qa_with_postgres.assistants_stream import EventHandler
from qa_with_postgres.assistants import client
from qa_with_postgres.langgraph_multiagent import message_queue, start_chatbot, start_chatbot_in_background


# Create a router object
router = APIRouter()
active_websockets = {}
client_id = None

@router.post("/upload", status_code=200)
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None
):    
    table_name = None
    pdf_name = None

    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    

    if file.filename.endswith('.csv'):
        table_name = re.sub(r'\.csv$', '', file.filename)
        table_name = table_name.replace('-', '_')
    else:
        pdf_name = re.sub(r'\.pdf$', '', file.filename)
        pdf_name = pdf_name.replace('-', '_')


    try:
        if table_name:
            ingest_csv(file_location, table_name)

        else:
            ingest_pdf(file_location, pdf_name)

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.delete("/delete-file", status_code=204)
async def delete_table(table: TableNameRequest , request: Request):
    table_name = table.table_name

    delete_task_table(table_name)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
        cur.close()
        conn.close()
        return 
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete table")


@router.get("/get-tables", status_code=200)
async def get_table_files(request: Request):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT c.relname AS table_name
            FROM pg_class c
            JOIN pg_description d ON c.oid = d.objoid
            WHERE c.relkind = 'r'  -- 'r' stands for ordinary table
            AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            AND d.description = 'source_type: csv';
        """)
        files = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

        return files
    
    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching tables.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.get("/get-pdfs", status_code=200)
async def get_pdf_files(request: Request):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT c.relname AS table_name
            FROM pg_class c
            JOIN pg_description d ON c.oid = d.objoid
            WHERE c.relkind = 'r'  -- 'r' stands for ordinary table
            AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            AND d.description = 'source_type: pdf';
        """)
        files = [row[0] for row in cur.fetchall()]

        print("PDF files:", files)

        cur.close()
        conn.close()

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
        await start_chatbot(table_name)
        websocket = active_websockets.get(client_id)
        await start_chatbot_in_background(table_name, websocket)
        
        return table_data
    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching table data.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")



@router.get("/status/{table_name}/{task_id}")
async def get_status(table_name: str, task_id: str):
    return get_task(table_name, task_id)


@router.websocket("/ws/chat-client")
async def websocket_endpoint(websocket: WebSocket):
    global client_id 
    await websocket.accept()
    client_id = str(id(websocket))
    active_websockets[client_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            await message_queue.put(data["message"])
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected: {e}")
    finally:
        del active_websockets[client_id]



async def fetch_messages(thread_id):
    try:
        paginator = client.beta.threads.messages.list(thread_id=thread_id)
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



