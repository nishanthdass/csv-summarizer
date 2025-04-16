from fastapi import HTTPException, UploadFile
import re
import os
from utils.pdf_processing_funct import process_pdf, post_process_pdf
from  db.kg_utility import process_pdf_to_kg
import shutil
import pymupdf
from config import postgres_var

task_completion_status = {}


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

