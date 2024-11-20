from main import app
import asyncio
from qa_with_postgres.db_utility import poll_completion_and_load_data

task_status = {}

@app.post("/start-task", status_code=202)
async def start_task(task_id: str):
    task_status[task_id] = "in_progress"
    asyncio.create_task(long_running_task(task_id))  # Run the task asynchronously
    return {"task_id": task_id, "status": "in_progress"}

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    status = task_status.get(task_id, "not_found")
    return {"task_id": task_id, "status": status}
