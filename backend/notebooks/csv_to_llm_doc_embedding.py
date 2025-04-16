from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from utilities import *
from credentials import *



def get_langchain_doc(table_name: str):
    doc = []
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        cur = conn.cursor()

        # get all rows
        cur.execute(f"SELECT * FROM {table_name};")
        rows = cur.fetchall()

        columns_types = get_all_columns_and_types(table_name)
        columns = ["id"] + [col[0] for col in columns_types]
        rprint(columns)

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

