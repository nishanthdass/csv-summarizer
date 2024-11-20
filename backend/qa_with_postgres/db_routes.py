from fastapi import APIRouter, HTTPException, File, UploadFile, Request, BackgroundTasks
import shutil
import psycopg2
import pandas as pd
import re
from qa_with_postgres.db_connect import get_db_connection
from qa_with_postgres.file_config import UPLOAD_DIR
from qa_with_postgres.models import TableNameRequest
from qa_with_postgres.db_utility import ingest_file, poll_completion_and_load_data, fetch_and_process_rows_with_embeddings, get_table_data, get_summary_data
from qa_with_postgres.chatbot import ChatBot

import asyncio



# Create a router object
router = APIRouter()

@router.post("/upload", status_code=200)
async def upload_file(
    file: UploadFile = File(...),
    request: Request = None
):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    table_name = re.sub(r'\.csv$', '', file.filename)

    try:
        # Ingest the file into the database
        ingest_file(file_location, table_name)

        await fetch_and_process_rows_with_embeddings(table_name)
        summary_data = await get_summary_data(table_name=table_name.lower() + "_summary")
        if summary_data:
            random_values_json = summary_data["repacked_rows"]
            ordered_values_json = summary_data["row_numbered_json"]


        return {"message": "File uploaded successfully"}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    

@router.delete("/delete-table", status_code=204)
async def delete_table(table: TableNameRequest , request: Request):
    table_name = table.table_name
    task_registry = request.app.state.task_registry
    
    try:
        request.app.state.workplace.stop_crew_thread("SummarizerCrewFlow")
        for table_name, tasks in task_registry.items():
            if table_name == table.table_name:
                for task in tasks:
                    if not task.done():
                        task.cancel()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
        cur.execute(f"DROP TABLE IF EXISTS {table_name}_summary")
        conn.commit()
        cur.close()
        conn.close()
        return 
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete table")


@router.get("/get-tables", status_code=200)
async def get_files():
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