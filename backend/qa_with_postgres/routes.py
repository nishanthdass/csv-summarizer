from fastapi import APIRouter, HTTPException, File, UploadFile, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import psycopg2
from qa_with_postgres.load_config import LoadPostgresConfig
from qa_with_postgres.models import TableNameRequest, PdfNameRequest
from qa_with_postgres.db_utility import ingest_csv_into_postgres, ingest_pdf_into_postgres, get_table_data
from qa_with_postgres.table_tasks import get_task, delete_task_table
from qa_with_postgres.langgraph_multiagent import message_queue, start_chatbot, start_chatbot_in_background
from rich import print as rprint
import os




# Create a router object
router = APIRouter()
db = LoadPostgresConfig()
active_websockets = {}



@router.post("/upload", status_code=200)
async def upload_file(file: UploadFile = File(...)):
    """
    Ingests a PDF or CSV file into a PostgreSQL table.
    """
    if file.filename.endswith('.csv'):
        ingest_csv_into_postgres(file)
    else:
        ingest_pdf_into_postgres(file)


# Refactor to send table_name via Request
@router.delete("/delete-file", status_code=204)
async def delete_table(table: TableNameRequest , request: Request):
    table_name = table.table_name

    delete_task_table(table_name)

    try:
        conn = db.get_db_connection()
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
        cur.close()
        conn.close()
        return 
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete table")


@router.get("/get-tables", status_code=200)
async def get_table_files(request: Request):
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT c.relname AS table_name
            FROM pg_class c
            JOIN pg_description d ON c.oid = d.objoid
            WHERE c.relkind = 'r'  -- 'r' stands for ordinary table
            AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            AND d.description = 'source_type: csv';
        """)
        files = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

        return files
    
    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching tables.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.get("/get-pdfs", status_code=200)
async def get_pdf_files(request: Request):
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()

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


        cur.close()
        conn.close()

        return table_content
    
    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching tables.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
# Refactor to send table_name via Request
@router.post("/get-table", status_code=200)
async def get_table(table: TableNameRequest, request: Request):
    table_name = table.table_name
    page = table.page
    page_size = table.page_size
    
    try:
        table_data = get_table_data(table_name, page, page_size)
        # await start_chatbot(table_name)
        # websocket = active_websockets.get(client_id)
        # await start_chatbot_in_background(table_name, websocket)
        
        return table_data
    except psycopg2.DatabaseError as e:
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching table data.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    

@router.get("/get-pdf/{pdf_name}")
async def get_pdf(pdf_name: str):
    print(pdf_name)


    try:
        conn = db.get_db_connection()
        cur = conn.cursor()

        cur.execute(f"SELECT to_regclass('{pdf_name}')")
        table_exists = cur.fetchone()[0]
        if not table_exists:
            raise HTTPException(status_code=404, detail=f"Table {pdf_name} not found.")

        cur.execute(f"SELECT {pdf_name + '.pdf_file_name'} FROM {pdf_name};")

        file_name = cur.fetchone()[0]

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    pdf_path = os.path.abspath(f"./uploaded_files/pdf_files/{pdf_name}/{file_name}")

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=pdf_name,
        content_disposition_type="inline"   
    )


@router.get("/status/{table_name}/{task_id}")
async def get_status(table_name: str, task_id: str):
    return get_task(table_name, task_id)


@router.websocket("/ws/chat-client")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    session = websocket.cookies.get("session")
    if not session:
        await websocket.close(code=4000, reason="Session not found")
        return
    
    client_id = str(id(websocket))
    active_websockets[client_id] = {
        "websocket": websocket,
        "session": session
    }

    try:
        while True:
            data = await websocket.receive_json()
            await message_queue.put(data["message"])
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected: {e}")
    finally:
        del active_websockets[client_id]
