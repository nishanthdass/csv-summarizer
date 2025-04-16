from fastapi import HTTPException, UploadFile
import re
import os
from utils.pdf_processing_funct import process_pdf, post_process_pdf
from  db.document.neo4j_utility import process_pdf_to_kg
import shutil
import pymupdf
from config import postgres_var

    
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

