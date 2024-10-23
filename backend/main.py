from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import psycopg2
import pandas as pd
import re
from dotenv import load_dotenv

app = FastAPI()

load_dotenv()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

UPLOAD_DIR = "./uploaded_files"  # Directory to store uploaded files
os.makedirs(UPLOAD_DIR, exist_ok=True)

# PostgreSQL connection parameters
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST')

# Connect to PostgreSQL
def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

DB_PORT = os.getenv('POSTGRES_PORT')

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    print("Received file:", file.filename)

    file_location = f"{UPLOAD_DIR}/{file.filename}"
    
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    table_name = re.sub(r'\.csv$', '', file.filename)

    try:
        ingest_file(file_location, table_name)  # Call your file processing function
    except Exception as e:
        return {"error": f"Failed to process file: {str(e)}"}
    
    return {"info": f"file '{file.filename}' saved at '{file_location}'"}


@app.get("/get-tables")
async def get_files():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    files = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return files  # Returns the list of filenames


def ingest_file(file_path: str, table_name: str):
    """
    Ingest the CSV file into a PostgreSQL table.
    This assumes the table does not exist in the database and needs to be created.
    """
    print(f"Ingesting {file_path} into table {table_name}")

    dtype_mapping = {
        'int64': 'INTEGER',
        'float64': 'FLOAT',
        'object': 'TEXT',  # assuming object columns are strings
        'bool': 'BOOLEAN',
        'datetime64[ns]': 'TIMESTAMP'
    }

    column_definitions = []

    # Load the CSV into a Pandas DataFrame (optional step)
    df = pd.read_csv(file_path)
    columns = df.columns
    column_types = df.dtypes

    print(columns, column_types)

    for col, dtype in zip(columns, column_types):
        postgres_type = dtype_mapping.get(str(dtype), 'TEXT')  # Default to TEXT if unknown type
        clean_col = sanitize_column_name(col)
        column_definitions.append(f"{clean_col} {postgres_type}")
    
    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    create_table_query += ", ".join(column_definitions) + ");"

    print(f"Executing query: {create_table_query}")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Try creating the table
        cur.execute(create_table_query)
        conn.commit()
        print(f"Table {table_name} created successfully (or already exists).")
    except Exception as e:
        # If there's an error, log it
        print(f"Error creating table {table_name}: {str(e)}")
        conn.rollback()
        cur.close()
        conn.close()
        return

    try:
        # Ingest the data into the newly created table
        with open(file_path, 'r', encoding='utf-8') as f:
            cur.copy_expert(f"COPY {table_name} FROM STDIN DELIMITER ',' CSV HEADER", f)
        conn.commit()
        print(f"Data successfully ingested into {table_name}")
    except Exception as e:
        # If there's an error during data ingestion, log it
        print(f"Error ingesting data into table {table_name}: {str(e)}")
        conn.rollback()

    # Close the cursor and connection
    cur.close()
    conn.close()



def sanitize_column_name(col_name: str) -> str:
    clean_col_name = re.sub(r'\W+', '_', col_name)  # Replace non-alphanumeric characters with "_"
    clean_col_name = clean_col_name.lower()
    
    return clean_col_name