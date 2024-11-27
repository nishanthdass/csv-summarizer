from fastapi import APIRouter, HTTPException, File, UploadFile, Request, BackgroundTasks
import shutil
import psycopg2
import pandas as pd
import re
from qa_with_postgres.db_connect import get_db_connection
from qa_with_postgres.file_config import UPLOAD_DIR
from qa_with_postgres.models import TableNameRequest, TableSummaryDataRequest
from qa_with_postgres.db_utility import ingest_file, fetch_and_process_rows_with_embeddings, get_table_data, get_summary_data
from qa_with_postgres.table_tasks import add_table, get_tasks_for_table, add_task, update_task, get_task, delete_task_table
# from qa_with_postgres.chatbot import ChatBot
import requests
import httpx
import asyncio
from typing import List, Dict
import uuid
import json


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

        await fetch_and_process_rows_with_embeddings(table_name)
        summary_data = await get_summary_data(table_name=table_name.lower() + "_summary")
        
        random_values_json = summary_data["repacked_rows"]
        ordered_values_json = summary_data["row_numbered_json"]

        task_id = str(uuid.uuid4())

        add_table(table_name.lower())
        add_task(table_name.lower(), task_id, "Create a general summary of all columns")
        update_task(table_name.lower(), task_id, "Started", None)
        tasks = get_tasks_for_table(table_name.lower())
        task = get_task(table_name.lower(), task_id)

        
        table_name_data = {"task_id": task_id, "table_name": table_name.lower(), "random_values_json": random_values_json, "ordered_values_json": ordered_values_json}
        async with httpx.AsyncClient() as client:
            # Post to the analyze endpoint
            analyze_url = f"http://127.0.0.1:5000/tables/{table_name.lower()}/analyze"
            analyze_response = await client.post(analyze_url, json=table_name_data)

            if analyze_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to analyze table")

        return {"task": task}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    

@router.delete("/delete-table", status_code=204)
async def delete_table(table: TableNameRequest , request: Request):
    table_name = table.table_name

    delete_task_table(table_name)

    try:
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
    
@router.post("/get-table-summary", status_code=200)
async def get_table(table: TableSummaryDataRequest, request: Request):
    table_name = table.table_name
    table_name = table_name.lower() + "_summary"
    try:
        summary_data = await get_summary_data(table_name)
        table_summary = summary_data["results"]
        table_summary_data = TableSummaryDataRequest(table_name=table_name, results=table_summary)

        return table_summary_data
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


@router.get("/status/{table_name}/{task_id}")
async def get_status(table_name: str, task_id: str):
    return get_task(table_name, task_id)



@router.post("/results/{table_name}")
async def receive_results(table_name: str, result: Dict):
    clean_result = result["result"]
    update_task(table_name, result["task_id"], result["status"], result["result"])
    print(clean_result)
    clean_result = clean_result.strip("```python").strip("```")
    clean_result = json.loads(clean_result)
    clean_result = clean_result["result"]
    print(clean_result)
    print(type(clean_result))
    if result["status"] == "Completed":
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


    return {"status": "success"}