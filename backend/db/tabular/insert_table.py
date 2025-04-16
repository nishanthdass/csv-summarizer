from utils.os_re_tools import remove_file_extension, create_folder_by_location, extract_table_name, save_uploaded_file
from db.tabular.postgres_utilities import insert_csv_into_table, add_fuzzystrmatch_extension, generate_column_definitions
from db.tabular.table_embeddings import get_docs_from_rows, create_embeddings_of_table_rows
from config import postgres_var
from fastapi import UploadFile
import pandas as pd




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
