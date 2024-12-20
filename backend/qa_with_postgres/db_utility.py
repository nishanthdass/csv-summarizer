from fastapi import HTTPException
import pandas as pd
import re
from qa_with_postgres.db_connect import get_db_connection, close_db_connection
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from qa_with_postgres.db_connect import get_db_connection
import json
from transformers import AutoModel
from psycopg2.extensions import register_adapter, AsIs
import numpy as np
import asyncio

task_completion_status = {}


def adapt_numpy_array(numpy_array):
    return AsIs("'[" + ",".join(map(str, numpy_array)) + "]'")

register_adapter(np.ndarray, adapt_numpy_array)

# chatbot_instance = ChatBot()
url_pattern = re.compile(
    r'^(https?://|www\.)'                  # Starts with 'http://', 'https://', or 'www.'
)



async def poll_completion_and_load_data(table_name, workplace):
    # Polling loop to check completion
    while not task_completion_status.get(table_name, False):
        print("Polling for completion...")
        await asyncio.sleep(1)  # Check every second

    # Task complete, call `load_summary_data`
    try:
        await workplace.load_summary_data(table_name)

    except Exception as e:
        return {"detail": f"An error occurred while fetching summary data: {str(e)}"}
    
async def stop_crew_flow(table_name, workplace):
    try:
        await workplace.stop_summarizer_crew_flow(table_name)
    except Exception as e:
        return {"detail": f"An error occurred while fetching summary data: {str(e)}"}

def setup_table_and_fetch_columns(conn, table_name):
    """Check if a table exists, setup necessary configurations, and fetch column names."""
    cur = conn.cursor()
    # setup_pgvector_and_table(conn)

    # Verify if the table exists
    cur.execute(f"SELECT to_regclass('{table_name}')")
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")

    # Fetch column names
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name.lower()}'")
    columns = [row[0] for row in cur.fetchall()]

    return cur, columns


async def fetch_and_process_rows_with_embeddings(table_name):
    """Fetch rows, process text into embeddings, and insert into the embeddings table."""
    conn = get_db_connection()
    cur, columns = setup_table_and_fetch_columns(conn, table_name)
    url_pattern = re.compile(r'^(https?://|www\.)')

    # Initialize repacked_rows as a dictionary where each key is a column name and values are lists of each row's items
    repacked_rows = {column: [] for column in columns}
    row_numbered_json = {}  # New dictionary to hold rows indexed by row number

    # Define sample size
    cur.execute(f"SELECT COUNT(*) AS total_rows FROM {table_name};")
    total_rows = cur.fetchone()[0]
    sample_size = min(int(total_rows * 0.05), 20000) if total_rows >= 100 else total_rows

    # Fetch rows with row index included
    cur.execute(f"""
        SELECT ROW_NUMBER() OVER() AS row_index, * 
        FROM {table_name} 
        ORDER BY random() 
        LIMIT {sample_size};
    """)
    rows = cur.fetchall()
    columns = ["row_index"] + [desc[0] for desc in cur.description[1:]]  # Include row_index in columns list

    for row in rows:
        row_data = {columns[i]: row[i] for i in range(len(columns))}
        
        for key, value in row_data.items():
            if isinstance(value, str) and not url_pattern.match(value) and len(value) > 100:
                chunks = []
                semantic_chunker = SemanticChunker(OpenAIEmbeddings(), breakpoint_threshold_type="percentile")
                semantic_chunks = semantic_chunker.create_documents([value])

                for chunk in semantic_chunks:
                    json_serializable_data = chunk.dict()
                    if "page_content" in json_serializable_data:
                        json_serializable_data = json_serializable_data["page_content"]
                        json_data = json.dumps(json_serializable_data)
                        chunks.append(json_data)

                row_data[key] = chunks
            else:
                row_data[key] = value  # No embedding; just add the value as is

            # Append the processed row value to the corresponding column list in repacked_rows
            if key != "row_index":  # Exclude row_index from repacked columns
                repacked_rows[key].append(row_data[key])

        # Use row_index as key for row_numbered_json
        row_numbered_json[row_data["row_index"]] = row_data

    # Pass repacked_rows and row_numbered_json to create_summary_table
    await create_summary_table(conn, table_name, columns, repacked_rows, row_numbered_json)

    task_completion_status[table_name] = True

    cur.close()
    conn.close()


async def create_summary_table(conn, table_name, columns, repacked_rows, row_numbered_json):
    """Create a summary table with columns for repacked_rows and summaries for each column."""
    summary_table_name = f"{table_name}_summary"
    cur = conn.cursor()

    # Drop the summary table if it already exists
    cur.execute(f"DROP TABLE IF EXISTS {summary_table_name};")

    # Create the summary table
    cur.execute(f"""
        CREATE TABLE {summary_table_name} (
            id SERIAL PRIMARY KEY,
            repacked_rows JSONB,            -- Store repacked rows as JSONB
            row_numbered_json JSONB,        -- Store row_numbered_json as JSONB
            table_summary TEXT DEFAULT '',  -- Column for overall table summary
            isSummarized BOOLEAN DEFAULT FALSE,  -- New boolean column indicating if the table is summarized
            results JSONB,                   -- JSONB object to json_dict results from Crew
            assistant_id VARCHAR(255),      -- New column for storing assistant_id
            vector_store_id VARCHAR(255),    -- New column for storing vector_store_id
            thread_id VARCHAR(255)         -- New column for storing thread_id

        );
    """)

    conn.commit()

    # Insert both repacked_rows and row_numbered_json into the row with id=1
    cur.execute(
        f"INSERT INTO {summary_table_name} (id, repacked_rows, row_numbered_json) VALUES (1, %s, %s);",
        (json.dumps(repacked_rows), json.dumps(row_numbered_json))  # Convert both to JSON format for insertion
    )

    conn.commit()
    print(f"Summary table '{summary_table_name}' created with initial data.")
    cur.execute(f"COMMENT ON TABLE {summary_table_name} IS 'agent table';")
    conn.commit()
    cur.close()

async def add_assistant_setting_to_db(table_name, assistant_id, vector_store_id, thread_id):
    summary_table_name = f"{table_name}_summary"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE {summary_table_name} SET assistant_id = %s, vector_store_id = %s, thread_id = %s WHERE id = 1;", (assistant_id, vector_store_id, thread_id))
    conn.commit()
    cur.close()


async def get_assistant_id(table_name):
    summary_table_name = f"{table_name}_summary"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT assistant_id FROM {summary_table_name} WHERE id = 1;")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

async def get_vector_store_id(table_name):
    summary_table_name = f"{table_name}_summary"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT vector_store_id FROM {summary_table_name} WHERE id = 1;")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

async def get_table_size(table_name):
    print("Fetching table size...: ", table_name)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT to_regclass('{table_name}')")
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")
    
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    table_size = cur.fetchone()[0]
    cur.close()
    conn.close()
    return table_size


async def get_summary_data(table_name):
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if the table exists
    cur.execute(f"SELECT to_regclass('{table_name}')")
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")

    # Fetch data as JSON from PostgreSQL
    query = f"""
        SELECT json_agg(json_build_object(
            id, to_jsonb({table_name}) - 'id'
        ))
        FROM {table_name};
    """
    cur.execute(query)
    result = cur.fetchone()[0]

    cur.close()
    conn.close()

    # Return the JSON object as a dictionary
    return result[0]["1"] if result else {}




def setup_pgvector_and_table(conn):
    try:
        cur = conn.cursor()
        
        # Check and create the pgvector extension if it doesn't exist
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
        
        # Check if the embeddings table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'embeddings'
            );
        """)
        table_exists = cur.fetchone()[0]

        # Create the embeddings table if it doesn't exist
        if not table_exists:
            cur.execute("""
                CREATE TABLE embeddings (
                    id SERIAL PRIMARY KEY,
                    reference_id VARCHAR,      -- Unique reference ID for linking back to original data
                    column_name VARCHAR,       -- Name of the column or context for the embedding
                    embedding vector(768)      -- Embedding vector column, adjust dimensions as needed
                );
            """)
            conn.commit()
            print("Created embeddings table with pgvector column.")
            cur.execute(f"COMMENT ON TABLE embeddings IS 'agent table';")
            conn.commit()
        else:
            print("Embeddings table already exists.")
        
        cur.close()

    except Exception as e:
        conn.rollback()
        print(f"Error setting up pgvector or embeddings table: {e}")

def get_table_data(table_name: str, page: int, page_size: int):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT to_regclass('{table_name}')")
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")

    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = cur.fetchone()[0]

    offset = (page - 1) * page_size

    cur.execute(f"SELECT *, ctid FROM {table_name} LIMIT {page_size} OFFSET {offset}")
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


def ingest_file(file_path: str, table_name: str):
    """
    Ingests the CSV file into a PostgreSQL table.
    This assumes the table does not exist and needs to be created.
    """
    dtype_mapping = {
        'int64': 'INTEGER',
        'float64': 'FLOAT',
        'object': 'TEXT',
        'bool': 'BOOLEAN',
        'datetime64[ns]': 'TIMESTAMP'
    }

    column_definitions = []

    df = pd.read_csv(file_path)
    columns = df.columns
    column_types = df.dtypes

    for col, dtype in zip(columns, column_types):
        postgres_type = dtype_mapping.get(str(dtype), 'TEXT')
        clean_col = sanitize_column_name(col)
        column_definitions.append(f"{clean_col} {postgres_type}")

    
    
    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    create_table_query += ", ".join(column_definitions) + ");"

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(create_table_query)
        conn.commit()
        cur.execute(f"COMMENT ON TABLE {table_name} IS 'frontend table';")
        conn.commit()
    except Exception as e:
        print(f"Error creating table {table_name}: {str(e)}")
        conn.rollback()
        cur.close()
        conn.close()
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            cur.copy_expert(f"COPY {table_name} FROM STDIN DELIMITER ',' CSV HEADER", f)
        conn.commit()
    except Exception as e:
        print(f"Error ingesting data into table {table_name}: {str(e)}")
        conn.rollback()
    finally:
        close_db_connection(conn)

    cur.close()
    conn.close()

def sanitize_column_name(col_name: str) -> str:
    return re.sub(r'\W+', '_', col_name).lower()

def convert_postgres_to_react(columns_and_types):
    postgres_to_react_map = {
        "text": "string",
        "boolean": "boolean",
        "integer": "number",
        "double precision": "number",
        "timestamp": "string",
        "float": "number",
    }

    for i in range(len(columns_and_types)):
        column_name, postgres_type = columns_and_types[i]
        react_type = postgres_to_react_map.get(postgres_type, "any")
        columns_and_types[i] = (column_name, react_type)

    return columns_and_types


async def if_table_exists(table_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT to_regclass('{table_name}')")
    table_exists = cur.fetchone()[0]
    cur.close()
    conn.close()
    return table_exists

async def add_thread_id(table_name, thread_id):
    summary_table = f"{table_name}_summary"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE {summary_table} SET thread_id = %s WHERE id = 1;", (thread_id,))
    conn.commit()
    cur.close()
    conn.close()

async def get_thread_id(table_name):
    summary_table = f"{table_name}_summary"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT thread_id FROM {summary_table} WHERE id = 1;")
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

async def remove_thread_id(table_name):
    summary_table = f"{table_name}_summary"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE {summary_table} SET thread_id = NULL WHERE id = 1;")
    conn.commit()
    cur.close()
    conn.close()