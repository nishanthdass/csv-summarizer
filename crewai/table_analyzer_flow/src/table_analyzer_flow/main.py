from fastapi import FastAPI, BackgroundTasks, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pydantic import BaseModel
from crewai.flow.flow import Flow, start
from crews.table_sumarizer_crew.table_sumarizer_crew import TableSummarizerCrew
from time import sleep
import os
from dotenv import load_dotenv
import json
import httpx
from table_summarizer_flow import TableSummarizerCrewFlow
from routes import router

os.environ['OTEL_SDK_DISABLED'] = 'true'



app = FastAPI()

load_dotenv()

DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')

print(f"Initializing TableSummarizerCrew...{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(router, prefix="/tables", tags=["Tables"])

for route in app.routes:
    print(f"Path: {route.path}, Name: {route.name}, Methods: {route.methods}")


