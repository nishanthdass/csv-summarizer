from utils.os_re_tools import sanitize_label
from config import postgres_var
import pandas as pd
from langchain_core.documents import Document



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

