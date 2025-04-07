from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from routers.routes import router
import os


load_dotenv()

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "default-secret-key")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="session",
    same_site="lax",
    max_age=None,
)

app.state.task_registry = {}


app.include_router(router)

@app.get("/set-session")
async def set_session(request: Request):
    request.session["user_data"] = {"name": "John Doe", "role": "admin"}
    return JSONResponse({"message": "Session data set"})


@app.get("/get-session")
async def get_session(request: Request):
    user_data = request.session.get("user_data")
    if not user_data:
        # Return 404 status with a message
        return JSONResponse(
            status_code=404,
            content={"message": "No session data found"}
        )
    return {"user_data": user_data}


@app.get("/clear-session")
async def clear_session(request: Request):
    request.session.clear()
    return {"message": "Session cleared"}

