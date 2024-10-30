import pandas as pd
import re
from qa_with_postgres.db_connect import get_db_connection, close_db_connection

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
