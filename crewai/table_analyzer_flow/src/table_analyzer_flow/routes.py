from fastapi import FastAPI, BackgroundTasks, HTTPException, APIRouter
from typing import List, Dict, Any
from pydantic import BaseModel
from table_summarizer_helper import table_analysis, run_table_analysis


router = APIRouter()

class TableData(BaseModel):
    table_name: str
    random_values_json: Dict[str, List[str]]
    ordered_values_json: Dict[int, Dict[str, str]]

# table_analysis: Dict[str, Dict[str, Any]] = {}

@router.get("/{table_name}/{task_id}/state")
async def get_flow_state(table_name: str, task_id: str):
    if table_name not in table_analysis or task_id not in table_analysis[table_name]:
        raise HTTPException(status_code=404, detail="Flow not found.")

    flow_entry = table_analysis[table_name][task_id]
    return {
        "state": flow_entry["flow"].state.dict() if flow_entry["flow"] else {},
        "status": flow_entry["status"],
        "result": flow_entry["result"],
    }


@router.get("/{table_name}/{task_id}/result")
async def get_result(table_name: str, task_id: str):
    if table_name not in table_analysis or task_id not in table_analysis[table_name]:
        raise HTTPException(status_code=404, detail="Task not found.")

    flow_entry = table_analysis[table_name][task_id]
    if flow_entry["result"]:
        return {"result": flow_entry["result"]}
    return {"result": "Analysis not complete or file not found"}


@router.post("/{table_name}/analyze")
async def analyze_table(table_name_data: Dict, background_tasks: BackgroundTasks):
    print("Received table data:", table_name_data)
    task_id = table_name_data["task_id"]
    table_name = table_name_data["table_name"]
    keys_to_list_json = table_name_data["random_values_json"]
    index_to_row_json = table_name_data["ordered_values_json"]

    if table_name not in table_analysis:
        table_analysis[table_name] = {}

    if task_id in table_analysis[table_name]:
        return {"message": f"Task {task_id} already exists for table {table_name}"}

    table_analysis[table_name][task_id] = {
        "status": "In Progress",
        "result": None,
        "flow": None,
    }
    background_tasks.add_task(run_table_analysis, task_id, keys_to_list_json, index_to_row_json, table_name)

    return {"message": f"Task {task_id} started for table {table_name}"}


@router.post("/{table_name}/{task_id}/retry")
async def retry_analysis(table_name: str, task_id: str, background_tasks: BackgroundTasks):
    if table_name not in table_analysis or task_id not in table_analysis[table_name]:
        raise HTTPException(status_code=404, detail="Task not found.")

    flow_entry = table_analysis[table_name][task_id]
    flow_entry["status"] = "Retrying"
    background_tasks.add_task(
        run_table_analysis,
        task_id,
        flow_entry["flow"].state.key_to_list_json,
        flow_entry["flow"].state.index_to_row_json,
        table_name,
    )

    return {"message": f"Retry triggered for task {task_id} on table {table_name}"}
