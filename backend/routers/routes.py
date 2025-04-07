from fastapi import APIRouter, HTTPException, File, UploadFile, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
import psycopg2
from config import LoadPostgresConfig
from models.models import TableNameRequest, PdfNameRequest, MessageInstance
from db.db_utility import ingest_csv_into_postgres, ingest_pdf_into_postgres, get_table_data, run_query
from services.tasks import get_task, delete_task_table
from llm_core.langgraph_stream import run_chatbots, active_websockets, tasks, manager, message_queue
from llm_core.src.utils.chatbot_manager import start_chatbot, set_table, set_pdf
from rich import print as rprint
import os
import re
import asyncio
from starlette.status import HTTP_401_UNAUTHORIZED


# Create a router object
router = APIRouter()
db = LoadPostgresConfig()


@router.post("/upload", status_code=200)
async def upload_file(file: UploadFile = File(...)):
    """
    Ingests a PDF or CSV file into a PostgreSQL table.
    """
    if file.filename.endswith('.csv'):
        ingest_csv_into_postgres(file)
    else:
        ingest_pdf_into_postgres(file)


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
    

@router.post("/get-table", status_code=200)
async def get_table(table: TableNameRequest, request: Request):
    table_name = table.table_name
    page = table.page
    page_size = table.page_size
    try: 
        session = await verify_session(request)
        print(f"chat_server for session: {session}")
    except Exception as e:
        print(f"Unexpected error in WebSocket endpoint: {e}")
    
    if not table_name:
        try:
            await set_table(session['name'], None, manager)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get table name")
    else:
        try:

            table_data = get_table_data(table_name, page, page_size)
            await set_table(session['name'], table_name, manager)
            
            return table_data
        except psycopg2.DatabaseError as e:
            print(f"Database error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error while fetching table data.")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.post("/set-pdf", status_code=200)
async def set_pdf_route(pdf_name: PdfNameRequest, request: Request):
    try: 
        session = await verify_session(request)
        print(f"chat_server for session: {session}")
    except Exception as e:
        print(f"Unexpected error in WebSocket endpoint: {e}")

    if not pdf_name.pdf_name:
        try:
            await set_pdf(session['name'], None, manager)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    else:
        try:
            conn = db.get_db_connection()
            cur = conn.cursor()

            cur.execute(f"SELECT to_regclass('{pdf_name.pdf_name}')")
            table_exists = cur.fetchone()[0]
            if not table_exists:
                raise HTTPException(status_code=404, detail=f"Table {pdf_name.pdf_name} not found.")

            cur.execute(f"SELECT {pdf_name.pdf_name + '.pdf_file_name'} FROM {pdf_name.pdf_name};")

            file_name = cur.fetchone()[0]
            file_name_minus_extension = re.sub(r'\.pdf$', '', file_name)

            cur.close()
            conn.close()
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        
        try:
            await set_pdf(session['name'], file_name_minus_extension, manager)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
  

@router.get("/get-pdf/{pdf_name}", status_code=200)
async def get_pdf(pdf_name: str, request: Request):
    try: 
        session = await verify_session(request)
    except Exception as e:
        print(f"Unexpected error in WebSocket endpoint: {e}")

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


@router.websocket("/ws/chat-client")
async def websocket_endpoint(websocket: WebSocket):
    """ Establishes a WebSocket connection and handles incoming chat messages. """
    session = {}
    try:
        session = await verify_session(websocket)
        await websocket.accept()  # Ensure WebSocket is accepted first

        if session['name'] not in active_websockets:
            active_websockets[session['name']] = websocket

        while True:
            data = await websocket.receive_json()  # Only use 'websocket'
            message = MessageInstance(**data)
            await message_queue.put(message)

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session: {session}")
    except Exception as e:
        print(f"Unexpected error in WebSocket endpoint: {e}")
    finally:
        print(f"Closing WebSocket connection for session: {session}")
        active_websockets.pop(session['name'], None)


@router.post("/chat-server")
async def chat_server(request: Request):
    """
    This endpoint is used to start the chatbot for a session.
    """
    try: 
        session = await verify_session(request)
    except Exception as e:
        print(f"Unexpected error in WebSocket endpoint: {e}")

    try:
        if session['name'] not in active_websockets:
            return {"message": "No active websockets for session: " + session['name']}
        
        if not tasks.get(session['name']):
            await start_chatbot(session['name'], manager)
            task = asyncio.create_task(run_chatbots(session['name']))
            tasks[session['name']] = task
        else:
            print("chat-server task already exists for session: ", session)
            task = tasks.get(session['name'])

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    

@router.post("/sql-query")
async def sql_query(request: Request):

    try: 
        session = await verify_session(request)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        body = await request.json()
        result = run_query(body['table_name'], body['query'], body['role'], body['query_type'])
        return JSONResponse(content={"success": True, "data": result})

    except Exception as e:
        rprint(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


async def verify_session(request: Request):
    if "user_data" not in request.session:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return request.session["user_data"]