from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start, or_, and_
from crews.table_sumarizer_crew.table_sumarizer_crew import TableSummarizerCrew
import json
import aiofiles
import os

os.environ['OTEL_SDK_DISABLED'] = 'true'

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class TableData(BaseModel):
    table_name: str
    random_values_json: Dict[str, List[str]]
    ordered_values_json: Dict[int, Dict[str, str]]

table_analysis: Dict[str, Dict[str, Any]] = {}

@app.get("/tables/{table_name}/state")
async def get_flow_state(table_name: str):
    if table_name not in table_analysis:
        raise HTTPException(status_code=404, detail="Flow not found.")

    # Access the flow instance from table_analysis
    flow_entry = table_analysis[table_name]
    flow = flow_entry["flow"]

    # Return the current state
    return {
        "state": flow.state.dict(),
        "status": flow_entry["status"],
        "result": flow_entry["result"],
    }


@app.get("/tables/{table_name}/result")
async def get_result(table_name: str):
    safe_table_name = "".join(x for x in table_name if x.isalnum())
    filename = f"{safe_table_name}_latest.txt"  # Assuming you save it with this pattern
    if os.path.exists(filename):
        with open(filename, "r") as file:
            content = file.read()
        return {"result": content}
    return {"result": "Analysis not complete or file not found"}

@app.post("/tables/{table_name}/analyze")
async def analyze_table(table_name_data: TableData, background_tasks: BackgroundTasks):
    # Immediate response to user
    keys_to_list_json = table_name_data.random_values_json
    index_to_row_json = table_name_data.ordered_values_json
    table_name = table_name_data.table_name
    message = f"I've started the flow to work on {table_name}"

    # Add the actual work to background tasks
    background_tasks.add_task(run_table_analysis, keys_to_list_json, index_to_row_json, table_name)

    return {"message": message}

@app.post("/tables/{table_name}/retry")
async def retry_analysis(table_name: str, background_tasks: BackgroundTasks):
    if table_name not in table_analysis:
        raise HTTPException(status_code=404, detail="Flow not found.")

    flow_entry = table_analysis[table_name]
    flow = flow_entry["flow"]

    # Update the status and re-trigger the flow
    flow_entry["status"] = "Retrying"
    background_tasks.add_task(run_table_analysis, flow_entry["flow"].state.key_to_list_json, flow_entry["flow"].state.index_to_row_json, table_name)

    return {"message": f"Retry triggered for table: {table_name}"}


async def run_table_analysis(key_to_list_json: Dict[str, List[str]], index_to_row_json: Dict[int, Dict[str, str]], table_name: str):
    # Check if flow already exists in table_analysis
    if table_name in table_analysis:
        flow_entry = table_analysis[table_name]
        flow = flow_entry["flow"]
        flow_entry["status"] = "In Progress"  # Update status for retry
    else:
        # Create a new flow and store it in table_analysis
        flow = TableSummarizerCrewFlow(table_name)
        table_analysis[table_name] = {
            "flow": flow,
            "status": "In Progress",
            "result": None,
        }

    try:
        # Dynamic inputs for the flow
        inputs = {
            "key_to_list_json": key_to_list_json,
            "index_to_row_json": index_to_row_json,
            "table_name": table_name,
            "summary_table_name": f"{table_name}_summary",
        }

        # Kickoff the flow and await the result
        result = await flow.summarize_columns_from_json(inputs)

        # Update the result and status in table_analysis
        table_analysis[table_name]["result"] = result
        table_analysis[table_name]["status"] = "Complete"

    except Exception as e:
        # Handle errors and update the status
        table_analysis[table_name]["status"] = "Failed"
        table_analysis[table_name]["result"] = str(e)
        print(f"An error occurred for table {table_name}: {e}")



class TableSummarizerCrewState(BaseModel):
    """State for TableSummarizerCrewFlow"""
    table_name: str = ""


class TableSummarizerCrewFlow(Flow[TableSummarizerCrewState]):
    def __init__(self, table_name: str):
        super().__init__()
        self.table_name = table_name

    @start()
    async def summarize_columns_from_json(self, inputs: Dict[str, Any]):
        try:
            self.state.table_name = self.table_name

            # Initialize the crew dynamically
            crew_instance = TableSummarizerCrew(table_name=self.table_name)

            # Use the crew instance to kickoff the summarizer agent
            result = await crew_instance.json_summarizer_agent().kickoff_async(inputs=inputs)

            return result
        except Exception as e:
            print("Error:", str(e))
            raise

