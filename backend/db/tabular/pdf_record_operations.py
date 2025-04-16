from config import postgres_var
from fastapi import HTTPException


def get_pdf_names_from_db():
    """
    Returns a list of PDF file names from the database.
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        SELECT c.relname AS table_name
        FROM pg_class c
        JOIN pg_description d ON c.oid = d.objoid
        WHERE c.relkind = 'r'  -- 'r' stands for ordinary table
        AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
        AND d.description = 'source_type: pdf';
        """)
        files = [row[0] for row in cur.fetchall()]

        table_content = []

        for file in files:
            cur.execute(f"SELECT * FROM {file}")
            pdf_file_name = cur.fetchall()
            res_obj = {"pdf_file_name": pdf_file_name[0][1],
                        "table_name": file}
            table_content.append(res_obj)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    cur.close()
    conn.close()

    return table_content

def get_pdf_data(pdf_name: str):
    """returns pdf file name minus extension from db"""
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT to_regclass('{pdf_name.pdf_name}')")
        table_exists = cur.fetchone()[0]
        if not table_exists:
            raise HTTPException(status_code=404, detail=f"Table {pdf_name.pdf_name} not found.")

        cur.execute(f"SELECT {pdf_name.pdf_name + '.pdf_file_name'} FROM {pdf_name.pdf_name};")

        file_name = cur.fetchone()[0]

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    cur.close()
    conn.close()

    return file_name