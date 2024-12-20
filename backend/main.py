from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from qa_with_postgres.db_routes import router
from qa_with_postgres.assistants import Assistants




app = FastAPI()

print("Loading environment variables...")

load_dotenv()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.task_registry = {}


app.state.assistants = Assistants()


app.include_router(router)
