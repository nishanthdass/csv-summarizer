from fastapi import HTTPException, UploadFile
from langchain_core.documents import Document
import pandas as pd
import psycopg2
import re
import os
from utils.pdf_processing_funct import process_pdf, post_process_pdf
from  db.kg_utility import process_pdf_to_kg
import shutil
import pymupdf
from rich import print as rprint
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from config import openai_var, postgres_var

task_completion_status = {}

def run_query(table_name: str, query: str, role: str, query_type: str):
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT to_regclass('{table_name}')")
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")
    
    filtered_llm_query_result = []
    # get all column names
    if query_type == "retrieval":
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}';")
        
        cur.execute(query)
        columns = cur.description
        values = cur.fetchall()

        llm_query_result = [dict(zip([col[0] for col in columns if col], row)) for row in values]


        for row in llm_query_result:
            filtered_llm_query_result.append(row)
            
    
    if query_type == "manipulation":
        cur.execute(query)
        conn.commit()

    return filtered_llm_query_result


def get_all_columns_and_types(table_name):
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    # Get primary key column(s)
    cur.execute(f"""
        SELECT a.attname
        FROM   pg_index i
        JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE  i.indrelid = '{table_name}'::regclass AND i.indisprimary;
    """)
    primary_keys = {row[0] for row in cur.fetchall()}

    # Get all columns excluding 'embedding' and primary keys
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
          AND column_name != 'embedding';
    """, (table_name,))
    all_columns = cur.fetchall()
    
    filtered_columns = [(col, dtype) for col, dtype in all_columns if col not in primary_keys]

    cur.close()
    conn.close()

    # Format output string
    response = ",".join(f"{col}({dtype})" for col, dtype in filtered_columns)
    return response

def get_all_columns_and_types_tuple(table_name):
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    # Get primary key column(s)
    cur.execute(f"""
        SELECT a.attname
        FROM   pg_index i
        JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE  i.indrelid = '{table_name}'::regclass AND i.indisprimary;
    """)
    primary_keys = {row[0] for row in cur.fetchall()}

    # Get all columns excluding 'embedding' and primary keys
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
          AND column_name != 'embedding';
    """, (table_name,))
    all_columns = cur.fetchall()
    
    filtered_columns = [(col, dtype) for col, dtype in all_columns if col not in primary_keys]

    cur.close()
    conn.close()

    return filtered_columns


def get_all_columns(table_name):
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()


def get_table_data(table_name: str, page: int, page_size: int):
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    # Check if table exists
    cur.execute(f"SELECT to_regclass(%s)", (table_name,))
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")

    # Get primary key column(s)
    cur.execute(f"""
        SELECT a.attname
        FROM   pg_index i
        JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE  i.indrelid = %s::regclass AND i.indisprimary;
    """, (table_name,))
    primary_keys = {row[0] for row in cur.fetchall()}

    # Get all column names excluding 'embedding' and primary key(s)
    cur.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s AND column_name != 'embedding';
    """, (table_name,))
    all_columns = [row[0] for row in cur.fetchall()]
    selected_columns = [col for col in all_columns if col not in primary_keys]

    # Get column names and types for header (excluding embedding and primary key)
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s AND column_name != 'embedding';
    """, (table_name,))
    all_column_types = cur.fetchall()
    filtered_column_types = [(col, dtype) for col, dtype in all_column_types if col not in primary_keys]
    columns_and_types = convert_postgres_to_react(filtered_column_types)

    # Total rows
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = cur.fetchone()[0]
    offset = (page - 1) * page_size

    # Fetch paginated rows (exclude primary key & embedding)
    column_list = ", ".join(selected_columns) + ", ctid"
    cur.execute(f"""
        SELECT {column_list}
        FROM {table_name}
        LIMIT %s OFFSET %s
    """, (page_size, offset))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    # Build the table object
    table_data = {
        "header": {col_name: col_type for col_name, col_type in columns_and_types},
        "rows": [dict(zip(columns, row)) for row in rows],
        "page": page,
        "page_size": page_size,
        "total_rows": total_rows,
        "total_pages": (total_rows + page_size - 1) // page_size
    }

    return table_data




def get_pdf_data(pdf_name: str):
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT to_regclass('{pdf_name}')")
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {pdf_name} not found.")
    
    cur.execute(f"SELECT pdf_file_path FROM {pdf_name};")

    file_path = cur.fetchone()[0]

    cur.close()
    conn.close()

    # Build the table object
    pdf_data = {
        "file_path": file_path
    }

    return pdf_data



def ingest_csv_into_postgres(file: UploadFile):
    """
    Ingests the CSV file into a PostgreSQL table.
    This assumes the table does not exist and needs to be created.
    """
    
    file_name = file.filename
    file_load = file.file
    table_name = re.sub(r'\.csv$', '', file_name)
    table_name = table_name.replace('-', '_')

    csv_upload_dir = f"./uploaded_files/csv_files/{table_name}"
    os.makedirs(csv_upload_dir, exist_ok=True)

    file_location = f"{csv_upload_dir}/{file_name}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file_load, buffer)


    dtype_mapping = {
        'int64': 'INTEGER',
        'float64': 'FLOAT',
        'object': 'TEXT',
        'bool': 'BOOLEAN',
        'datetime64[ns]': 'TIMESTAMP'
    }

    column_definitions = []

    df = pd.read_csv(file_location)
    columns = df.columns
    column_types = df.dtypes
    column_list = ", ".join(sanitize_column_name(col) for col in columns)


    column_definitions = ["id SERIAL PRIMARY KEY"]

    for col, dtype in zip(columns, column_types):
        postgres_type = dtype_mapping.get(str(dtype), 'TEXT')
        clean_col = sanitize_column_name(col)
        column_definitions.append(f"{clean_col} {postgres_type}")


    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    try:
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ("
        create_table_query += ", ".join(column_definitions) + ");"
        cur.execute(create_table_query)
        conn.commit()
        cur.execute(f"COMMENT ON TABLE {table_name} IS 'source_type: csv';")
        conn.commit()
    except Exception as e:
        print(f"Error creating table {table_name}: {str(e)}")
        conn.rollback()
        cur.close()
        conn.close()
        return

    try:
        with open(file_location, 'r', encoding='utf-8') as f:
            cur.copy_expert(
                        f"COPY {table_name} ({column_list}) FROM STDIN DELIMITER ',' CSV HEADER", f )
        conn.commit()
    except Exception as e:
        print(f"Error ingesting data into table {table_name}: {str(e)}")
        conn.rollback()

    try:
        # Add column for embedding ALTER TABLE items ADD COLUMN embedding vector(512);
        cur.execute(f"CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;")
        conn.commit()
    except Exception as e:
        print(f"Error adding embedding column to table {table_name}: {str(e)}")
        conn.rollback()

    try:
        create_embeddings_via_langchain(table_name)
    except Exception as e:
        print(f"Error creating embeddings for table {table_name}: {str(e)}")

    finally:
        cur.close()
        conn.close()
        postgres_var.close_db_connection(conn)


def create_embeddings_via_langchain(table_name: str):
    docs = get_langchain_doc(table_name)

    collection_name = table_name + "_collection"
    
    embeddings = OpenAIEmbeddings(
        openai_api_key=openai_var.openai_api_key,
        openai_api_base=openai_var.openai_endpoint,
        model=openai_var.openai_embedding_modal_small,
        dimensions=512
        )

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=postgres_var.get_db_url(),
    )

    id_str = str(table_name) + "_id"
    rprint(id_str)

    vector_store.add_documents(docs, ids=[doc.metadata[id_str] for doc in docs])


def get_langchain_doc(table_name: str):
    doc = []
    try:
        conn = postgres_var.get_db_connection()
        cur = conn.cursor()

        # get all rows
        cur.execute(f"SELECT * FROM {table_name};")
        rows = cur.fetchall()

        columns_types = get_all_columns_and_types_tuple(table_name)
        columns = ["id"] + [col[0] for col in columns_types]
        def format_row_with_columns(columns, row):
            return ", ".join([f"The {col} is {val}" for col, val in zip(columns, row)])

        for row in rows:
            text = format_row_with_columns(columns[1:], row[1:]) 
            metadata = {str(col): str(val) for col, val in zip(columns, row)}
            
            # Add concatenated ID
            metadata[f"{table_name}_id"] = f"{table_name}_{row[0]}"
            del metadata["id"]

            doc.append(Document(page_content=text, metadata=metadata))

    except Exception as e:
        print(f"Error getting rows from table {table_name}: {str(e)}")
        conn.rollback()

    return doc



def get_rows_by_id(table_name: str, row_id: int):
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    # Get actual column names (excluding 'embedding')
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s AND column_name != 'embedding';
    """, (table_name,))
    columns = [row[0] for row in cur.fetchall()]

    # Build a SELECT statement with those columns
    column_list = ", ".join(columns)

    cur.execute(
        f"SELECT {column_list} FROM {table_name} WHERE id = %s",
        (row_id,)
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    # Return row as a dictionary or None if not found
    return dict(zip(columns, row)) if row else None

    
def ingest_pdf_into_postgres(file: UploadFile):
    """
    Ingests a PDF file's path into a PostgreSQL table as TEXT.
    """
    
    file_name = file.filename
    file_load = file.file

    pdf_name = re.sub(r'\.pdf$', '', file_name)
    file_name_minus_extension = pdf_name
    pdf_name = re.sub(r'[^a-zA-Z0-9]+', '_', pdf_name)

    pdf_upload_dir = f"./uploaded_files/pdf_files/{pdf_name}"
    os.makedirs(pdf_upload_dir, exist_ok=True)

    image_output_path = pdf_upload_dir + "/images"
    os.makedirs(image_output_path, exist_ok=True)

    file_location = f"{pdf_upload_dir}/{file.filename}"

    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file_load, buffer)

    complete_path = pdf_upload_dir + "/" + file_name

    pdf_file = pymupdf.open(complete_path, filetype="pdf")
    page_nums = None
    pdf_obj = process_pdf(pdf_file, complete_path, page_nums)
    pdf_obj = post_process_pdf(pdf_obj)
    process_pdf_to_kg(pdf_obj, pdf_name)


    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    # Create the table with a TEXT column for storing the file path
    create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {pdf_name} (
            id SERIAL PRIMARY KEY,
            pdf_file_name TEXT
        );
    """

    try:
        # Create table
        cur.execute(create_table_query)
        conn.commit()

        # Add metadata to the table
        cur.execute(f"COMMENT ON TABLE {pdf_name} IS 'source_type: pdf';")
        conn.commit()

        # Insert the file path into the table
        insert_query = f"""
            INSERT INTO {pdf_name} (pdf_file_name) 
            VALUES (%s);
        """
        cur.execute(insert_query, (file_name,))
        conn.commit()

        print(f"PDF file '{file_name}' successfully ingested into table '{pdf_name}'.")
    except Exception as e:
        print(f"Error ingesting PDF data into table {pdf_name}: {str(e)}")
        conn.rollback()
    finally:
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

       
