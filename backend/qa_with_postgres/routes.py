from fastapi import APIRouter, HTTPException, File, UploadFile
import shutil
import psycopg2
import pandas as pd
import re
from qa_with_postgres.db_connect import get_db_connection, close_db_connection
from qa_with_postgres.config import UPLOAD_DIR
from qa_with_postgres.models import TableNameRequest
from qa_with_postgres.db_utility import ingest_file, sanitize_column_name, convert_postgres_to_react

# Create a router object
router = APIRouter()


@router.post("/upload", status_code=200)
async def upload_file(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    
    # Save the uploaded file
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    table_name = re.sub(r'\.csv$', '', file.filename)

    try:
        ingest_file(file_location, table_name)
    except Exception as e:
        # Return a 500 error if ingestion fails
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
    
    # Success response
    return {"info": f"file '{file.filename}' saved at '{file_location}'"}



@router.get("/get-tables", status_code=200)
async def get_files():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
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
    print(table_name, page, page_size)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(f"SELECT to_regclass('{table_name}')")
        table_exists = cur.fetchone()[0]
        if not table_exists:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")

        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = cur.fetchone()[0]

        offset = (page - 1) * page_size

        cur.execute(f"SELECT * FROM {table_name} LIMIT {page_size} OFFSET {offset}")
        rows = cur.fetchall()

        # Get the column names from the cursor description (ensures correct order)
        columns = [desc[0] for desc in cur.description]

        # Convert column types to React-compatible types (e.g., from information_schema if needed)
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}';
        """)
        columns_and_types = cur.fetchall()
        columns_and_types = convert_postgres_to_react(columns_and_types)

        cur.close()
        conn.close()

        # Build the table object
        table_data = {
            "header": {col_name: col_type for col_name, col_type in columns_and_types},  # Create header as a key-value map
            "rows": [dict(zip(columns, row)) for row in rows],  # Use correct column ordering from cur.description
            "page": page,
            "page_size": page_size,
            "total_rows": total_rows,
            "total_pages": (total_rows + page_size - 1) // page_size
        }

        return table_data  # Return table object with columns and rows
    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching table data.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

