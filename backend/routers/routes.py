from fastapi import APIRouter, HTTPException, File, UploadFile, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
import asyncio
from starlette.status import HTTP_401_UNAUTHORIZED
from rich import print as rprint

# import tabular db functions
from db.tabular.insert_table import ingest_csv_into_postgres
from db.tabular.table_operations import run_query, get_table_data, delete_table, get_table_names_from_db
from db.tabular.insert_pdf_record import ingest_pdf_into_postgres
from db.tabular.pdf_record_operations import get_pdf_names_from_db, get_pdf_data

# import os and task related functions
from utils.os_re_tools import remove_file_extension, set_abs_path, if_path_exists
from services.tasks import delete_task_table

# import llm related functions
from llm_core.langgraph_stream import run_chatbots, active_websockets, tasks, manager, message_queue
from llm_core.src.llm_utils.chatbot_manager import start_chatbot, set_table, set_pdf
from models.models import TableNameRequest, PdfNameRequest, MessageInstance


router = APIRouter()

@router.post("/upload", status_code=200)
async def upload_file(file: UploadFile = File(...)):
    """
    Ingests a PDF or CSV file into a PostgreSQL table.
    ingest_csv_into_postgres stores file, adds csv to table and creats/stores embeddings in vector store
    ingest_pdf_into_postgres stores file, adds pdf file location to table and creates/stores embeddings in neo4j
    """
    if file.filename.endswith('.csv'):
        ingest_csv_into_postgres(file)
    else:
        ingest_pdf_into_postgres(file)


@router.delete("/delete-file", status_code=204)
async def delete_table(table: TableNameRequest , request: Request):
    """
    Deletes a table from the database.
    Does not delete embeddings from vector store
    """
    table_name = table.table_name
    delete_task_table(table_name)
    delete_table(table_name)


@router.get("/get-tables", status_code=200)
async def get_table_files(request: Request):
    """
    Returns a list of table names from the database.
    """
    try:
        table_names = get_table_names_from_db()
        return table_names
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.get("/get-pdfs", status_code=200)
async def get_pdf_files(request: Request):
    """
    Returns a list of pdf names from the database.
    """
    try:
        table_content = get_pdf_names_from_db()
        return table_content
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    

@router.post("/get-table", status_code=200)
async def get_table(table: TableNameRequest, request: Request):
    """
    Set selected table in chatbot manager and return table data
    """
    table_name = table.table_name
    page = table.page
    page_size = table.page_size
    try: 
        session = await verify_session(request)
        print(f"chat_server for session: {session}")
    except Exception as e:
        print(f"Unexpected error in WebSocket endpoint: {e}")
    
    # handles when user unselects table
    if not table_name:
        try:
            await set_table(session['name'], None, manager)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get table name")
    else:
        # handles when user selects table
        try:
            table_data = get_table_data(table_name, page, page_size)
            await set_table(session['name'], table_name, manager)
            return table_data
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.post("/set-pdf", status_code=200)
async def set_pdf_route(pdf_name: PdfNameRequest, request: Request):
    """Set selected pdf in chatbot manager and return pdf data"""
    try: 
        session = await verify_session(request)
    except Exception as e:
        print(f"Unexpected error in WebSocket endpoint: {e}")

    # handles when user unselects pdf
    if not pdf_name.pdf_name:
        try:
            await set_pdf(session['name'], None, manager)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    else:
        # handles when user selects pdf
        try:
            file_name_minus_extension = remove_file_extension(get_pdf_data(pdf_name))
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
    """serves pdf file"""
    try: 
        session = await verify_session(request)
    except Exception as e:
        print(f"Unexpected error in WebSocket endpoint: {e}")

    try:
        file_name = get_pdf_data(pdf_name)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
    pdf_path = set_abs_path(f"./uploaded_files/pdf_files/{pdf_name}/{file_name}")

    if not if_path_exists(pdf_path):
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
    """
    This endpoint is used to run SQL queries.
    """

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
    """
    Verifies the session and returns the user data.
    """
    if "user_data" not in request.session:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return request.session["user_data"]