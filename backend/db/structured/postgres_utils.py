from utils.os_tools import sanitize_label, remove_file_extension, create_folder_by_location, extract_table_name, save_uploaded_file
from config import postgres_var
from llm_core.src.utils.embedding_utils import get_embedder
from fastapi import UploadFile
import pandas as pd
from fastapi import HTTPException, UploadFile
from langchain_core.documents import Document
from langchain_postgres import PGVector



def ingest_csv_into_postgres(file: UploadFile):
    """
    Ingests the CSV file into a PostgreSQL table.
    This assumes the table does not exist and needs to be created.
    """
    # upload file to server
    table_name, file_location = handle_csv_upload(file)
  
    # create table with column definitions
    column_list = create_table_from_csv(table_name, file_location)

    # insert data into table
    insert_csv_into_table(table_name, file_location, column_list)

    # add fuzzystrmatch extension to table
    add_fuzzystrmatch_extension()

    # create and store embeddings in PG vector store
    docs = get_docs_from_rows(table_name)
    create_embeddings_of_table_rows(table_name, docs)


def create_embeddings_of_table_rows(table_name: str, docs: list):
    """
    Creates embeddings of the rows in the table. To be used for similarity search of table rows.
    """
    try:
        collection_name = table_name + "_collection"
        vector_store = PGVector(
            embeddings=get_embedder(512),
            collection_name=collection_name,
            connection=postgres_var.get_db_url(),
        )
        id_str = str(table_name) + "_id"
        vector_store.add_documents(docs, ids=[doc.metadata[id_str] for doc in docs])
    except Exception as e:
        print(f"Error creating embeddings for table {table_name}: {str(e)}")


def add_fuzzystrmatch_extension():
    """
    Adds the fuzzystrmatch extension to the database.
    Allows for fuzzy matching of strings through methods like levenshtein distance.
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(f"Error adding fuzzystrmatch extension: {str(e)}")
    finally:
        cur.close()
        postgres_var.close_db_connection(conn)



def create_table_from_csv(table_name: str, file_location: str) -> str:
    """
    Creates a table using csv file name as table name
    Returns list of column names as string
    """
    column_definitions, column_string = generate_column_definitions(pd.read_csv(file_location))

    conn = postgres_var.get_db_connection()
    cur = conn.cursor()
    try:
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_definitions)});"
        cur.execute(create_table_query)
        cur.execute(f"COMMENT ON TABLE {table_name} IS 'source_type: csv';")
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(f"Error creating table: {str(e)}")
    finally:
        cur.close()
        postgres_var.close_db_connection(conn)

    return column_string


def insert_csv_into_table(table_name: str, file_location: str, column_list: str):
    """
    Inserts data from a CSV file into a PostgreSQL table.
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()
    try:
        with open(file_location, 'r', encoding='utf-8') as f:
            cur.copy_expert(
                f"COPY {table_name} ({column_list}) FROM STDIN DELIMITER ',' CSV HEADER", f)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(f"Error inserting data: {str(e)}")
    finally:
        cur.close()
        postgres_var.close_db_connection(conn)


def handle_csv_upload(file: UploadFile) -> tuple[str, str]:
    """
    Upload CSV to server and return (table_name, file_location)
    """
    file_name = file.filename
    table_name = extract_table_name(remove_file_extension(file_name))
    csv_upload_dir = f"./uploaded_files/csv_files/{table_name}"
    create_folder_by_location(csv_upload_dir)
    file_location = save_uploaded_file(file, csv_upload_dir)
    return table_name, file_location


def map_dtype_to_postgres(dtype: str) -> str:
    """
    Maps a pandas dtype to a PostgreSQL data type.
    """
    mapping = {
        'int64': 'INTEGER',
        'float64': 'FLOAT',
        'object': 'TEXT',
        'bool': 'BOOLEAN',
        'datetime64[ns]': 'TIMESTAMP'
    }
    return mapping.get(dtype, 'TEXT')


def generate_column_definitions(df: pd.DataFrame) -> tuple[list, str]:
    """
    Returns a list of column definitions for Postgres table creation
    and a comma-separated column string.
    """
    column_definitions = ["id SERIAL PRIMARY KEY"]
    sanitized_columns = []

    for col, dtype in zip(df.columns, df.dtypes):
        postgres_type = map_dtype_to_postgres(str(dtype))
        clean_col = sanitize_label(col)
        column_definitions.append(f"{clean_col} {postgres_type}")
        sanitized_columns.append(clean_col)

    return column_definitions, ", ".join(sanitized_columns)


def fetch_all_rows_from_table(table_name: str) -> list[tuple]:
    """
    Fetches all rows from a table and returns a list of tuples.
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM {table_name};")
        return cur.fetchall()
    except Exception as e:
        print(f"Error fetching rows from {table_name}: {str(e)}")
        conn.rollback()
        return []
    finally:
        cur.close()
        conn.close()



def format_row_as_text(columns: list[str], row: tuple) -> str:
    """
    Formats a row of data into a human-readable text.
    """
    return ", ".join([f"The {col} is {val}" for col, val in zip(columns, row)])


def get_docs_from_rows(table_name: str) -> list[Document]:
    """
    Fetches all rows from a table and converts them into Langchain Documents.
    Returns a list of Documents.
    """
    rows = fetch_all_rows_from_table(table_name)
    columns_types = get_all_columns_and_types(table_name)
    columns = ["id"] + [col[0] for col in columns_types]
    return create_langchain_docs_from_rows(table_name, rows, columns)


def create_langchain_docs_from_rows(table_name: str, rows: list[tuple], columns: list[str]) -> list[Document]:
    """
    Creates Langchain Documents from a list of rows and columns.
    Returns a list of Documents.
    """   
    docs = []

    for row in rows:
        text = format_row_as_text(columns[1:], row[1:])  # Skip id for text
        metadata = {col: str(val) for col, val in zip(columns, row)}
        
        # Create Unique ID
        metadata[f"{table_name}_id"] = f"{table_name}_{row[0]}"
        del metadata["id"]

        docs.append(Document(page_content=text, metadata=metadata))

    return docs


def run_query(table_name: str, query: str, role: str, query_type: str)-> list[str]:
    """
    Runs a query on a table and returns the results as a list of strings.
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT to_regclass('{table_name}')")
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")
    
    filtered_llm_query_result = []
    
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
    """
    Fetches all columns and their data types from a table.
    """
    filtered_columns = []
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    try:
        # Get all columns and their data types
        cur.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s;
        """, (table_name,))
        all_columns = cur.fetchall()
        filtered_columns = [(col, dtype) for col, dtype in all_columns]

    except Exception as e:
        print(f"Error fetching columns from {table_name}: {str(e)}")
        conn.rollback()

    cur.close()
    conn.close()

    return filtered_columns


def get_primary_key(table_name: str) -> str:
    """
    Fetches the primary key column from a table.
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    try:
        # Get primary key column(s)
                # Get primary key column(s)
        cur.execute(f"""
            SELECT a.attname
            FROM   pg_index i
            JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE  i.indrelid = '{table_name}'::regclass AND i.indisprimary;
        """)
        primary_keys = {row[0] for row in cur.fetchall()}

    except Exception as e:
        print(f"Error fetching primary key from {table_name}: {str(e)}")
        conn.rollback()

    cur.close()
    conn.close()

    return primary_keys


def get_table_data(table_name: str, page: int, page_size: int):
    """
    Fetches data from a table and returns it as a list of dictionaries.
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    # Check if table exists
    cur.execute(f"SELECT to_regclass(%s)", (table_name,))
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")

    # Get primary key column
    cur.execute(f"""
        SELECT a.attname
        FROM   pg_index i
        JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE  i.indrelid = %s::regclass AND i.indisprimary;
    """, (table_name,))
    primary_keys = {row[0] for row in cur.fetchall()}

    # Get all column names and primary key
    cur.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s;
    """, (table_name,))
    all_columns = [row[0] for row in cur.fetchall()]
    selected_columns = [col for col in all_columns if col not in primary_keys]

    # Get column names and types for header (excluding embedding and primary key)
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s;
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
