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


table_analysis: Dict[str, Dict[str, Any]] = {}

async def run_table_analysis(task_id: str, key_to_list_json: Dict[str, List[str]], index_to_row_json: Dict[int, Dict[str, str]], table_name: str):
    if table_analysis[table_name][task_id]["flow"] is not None:
        print(f"Resuming analysis for table {table_name}_{task_id}...")
        flow_entry = table_analysis[table_name][task_id]
    else:
        flow = TableSummarizerCrewFlow(table_name)
        
        table_analysis[table_name][task_id] = {
            "flow": flow,
            "status": "In Progress",
            "result": None,
        }
        flow_entry = table_analysis[table_name][task_id]

    try:
        inputs = {
            "key_to_list_json": key_to_list_json,
            "index_to_row_json": index_to_row_json,
            "table_name": table_name,
            "summary_table_name": f"{table_name}_summary",
        }
        print(f"Starting analysis for table {table_name}_{task_id}...")
        print(flow_entry)
        result = await flow_entry["flow"].summarize_columns_from_json(inputs)
        flow_entry["result"] = result
        flow_entry["status"] = "Completed"
        await send_results_to_backend(table_name, {"task_id": task_id, "status": "Completed", "result": result.raw})
    except Exception as e:
        flow_entry["status"] = "Failed"
        flow_entry["result"] = str(e)
        print(f"An error occurred for table {table_name}_{task_id}: {e}")
        await send_results_to_backend(table_name, {"task_id": task_id, "status": "Failed", "result": str(e)})


async def send_results_to_backend(table_name: str, result: Dict):
    try:
        url = f"http://127.0.0.1:8000/results/{table_name}"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=result)
        print(f"Result sent to backend for table {table_name}: {response.status_code}")
    except Exception as e:
        print(f"Failed to send results to backend: {e}")