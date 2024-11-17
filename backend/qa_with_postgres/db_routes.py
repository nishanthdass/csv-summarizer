from fastapi import APIRouter, HTTPException, File, UploadFile, Request, BackgroundTasks
import shutil
import psycopg2
import pandas as pd
import re
from qa_with_postgres.db_connect import get_db_connection
from qa_with_postgres.file_config import UPLOAD_DIR
from qa_with_postgres.models import TableNameRequest
from qa_with_postgres.db_utility import ingest_file, poll_completion_and_load_data, fetch_and_process_rows_with_embeddings, get_table_data
from qa_with_postgres.chatbot import ChatBot



# Create a router object
router = APIRouter()

# Main code in endpoint
@router.post("/upload", status_code=200)
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks(), request: Request = None):
    
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    table_name = re.sub(r'\.csv$', '', file.filename)

    try:
        # Ingest the entire file into the database for retrival
        ingest_file(file_location, table_name)

        # After adding csv to db, fetch_and_process_rows_with_embeddings will provide random datasample for agents to summarize table
        background_tasks.add_task(fetch_and_process_rows_with_embeddings, table_name)

        workplace = request.app.state.workplace

        #  poll_completion_and_load_data will intialize the summarization crew in the CrewAI workplace
        background_tasks.add_task(poll_completion_and_load_data, table_name, workplace)

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    return {"info": f"file '{file.filename}' saved at '{file_location}'"}


@router.get("/get-tables", status_code=200)
async def get_files():
    try:
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
async def get_table(request: TableNameRequest):
    table_name = request.table_name
    page = request.page
    page_size = request.page_size
    
    try:
        table_data = get_table_data(table_name, page, page_size)
        return table_data
    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching table data.")
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