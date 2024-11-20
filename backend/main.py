from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from qa_with_postgres.db_routes import router
from database_crew.src.database_crew.workplace import Workplace

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
app.state.workplace = Workplace()


app.include_router(router)

@app.get("/test-workplace")
async def test_workplace():
    workplace = Workplace()
    table_name = "housing"  # Example table name
    try:
        result = await workplace.load_summary_data(table_name)  # Capture the returned result
        return result
    except Exception as e:
        return {"detail": f"An error occurred while fetching summary data: {str(e)}"}
