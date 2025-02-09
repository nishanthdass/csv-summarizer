from fastapi import HTTPException, UploadFile
import pandas as pd
import re
import os
from config import LoadPostgresConfig
from utils.pdf_processing_funct import process_pdf
from  db.kg_utility import process_pdf_to_kg
import shutil
import pymupdf
from rich import print as rprint

task_completion_status = {}
db = LoadPostgresConfig()


# async def poll_completion_and_load_data(table_name, workplace):
#     # Polling loop to check completion
#     while not task_completion_status.get(table_name, False):
#         print("Polling for completion...")
#         await asyncio.sleep(1)  # Check every second

#     # Task complete, call `load_summary_data`
#     try:
#         await workplace.load_summary_data(table_name)

#     except Exception as e:
#         return {"detail": f"An error occurred while fetching summary data: {str(e)}"}

def get_all_columns_and_types(table_name):

    columns_and_types = []
    conn = db.get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}';")
    columns_and_types = cur.fetchall()

    cur.close()
    conn.close()

    response = ""
    for i in range(len(columns_and_types)):
        column_name, postgres_type = columns_and_types[i]
        response +=  str(column_name) + "(" + str(postgres_type) + ") + ,"

    return response


def run_query(table_name: str, query: str):
    conn = db.get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT to_regclass('{table_name}')")
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")
    
    # get all column names
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}';")
    column_names = [row[0] for row in cur.fetchall()]
    
    cur.execute(query)
    columns = cur.description
    values = cur.fetchall()

    llm_query_result = [dict(zip([col[0] for col in columns if col], row)) for row in values]

    filtered_llm_query_result = []

    for row in llm_query_result:
        row = {key: value for key, value in row.items() if key == 'ctid' or (key in column_names)}
        filtered_llm_query_result.append(row)


    cur.close()
    conn.close()

    return filtered_llm_query_result

def get_table_data(table_name: str, page: int, page_size: int):
    conn = db.get_db_connection()
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
    columns = [desc[0] for desc in cur.description]

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
        "header": {col_name: col_type for col_name, col_type in columns_and_types},
        "rows": [dict(zip(columns, row)) for row in rows],
        "page": page,
        "page_size": page_size,
        "total_rows": total_rows,
        "total_pages": (total_rows + page_size - 1) // page_size
    }

    return table_data


def get_pdf_data(pdf_name: str):
    conn = db.get_db_connection()
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

    for col, dtype in zip(columns, column_types):
        postgres_type = dtype_mapping.get(str(dtype), 'TEXT')
        clean_col = sanitize_column_name(col)
        column_definitions.append(f"{clean_col} {postgres_type}")

    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    create_table_query += ", ".join(column_definitions) + ");"

    conn = db.get_db_connection()
    cur = conn.cursor()

    try:
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
            cur.copy_expert(f"COPY {table_name} FROM STDIN DELIMITER ',' CSV HEADER", f)
        conn.commit()
    except Exception as e:
        print(f"Error ingesting data into table {table_name}: {str(e)}")
        conn.rollback()
    finally:
        db.close_db_connection(conn)

    cur.close()
    conn.close()


    
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
    pdf_obj = process_pdf(pdf_file, complete_path, page_nums, image_output_path, file_name_minus_extension)

    # rprint(pdf_obj)
    
    process_pdf_to_kg(pdf_obj, file_name_minus_extension)

    conn = db.get_db_connection()
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

        sanitize_pdf_name = pdf_name.replace('-', '_')

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



