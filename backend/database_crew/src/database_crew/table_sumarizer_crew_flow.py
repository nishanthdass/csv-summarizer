from typing import List, Dict, Any
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start, or_, and_
from .crews.database_crew.table_sumarizer_crew import TableSummarizerCrew
import json
import os

os.environ['OTEL_SDK_DISABLED'] = 'true'



class TableSummarizerCrewState(BaseModel):
    """State for TableSummarizerCrewFlow"""
    table_name: str = ""
    summary_table_name: str = ""
    key_to_list_json: Dict[str, Any] = {}
    index_to_row_json: Dict[str, Any] = {}
    isSummaryRunning: bool = False

class TableSummarizerCrewFlow(Flow[TableSummarizerCrewState]):
    def __init__(self, crew_instance: TableSummarizerCrew, table_name: str = "", summary_table_name: str = "", key_to_list_json: Dict[str, Any] = {}, index_to_row_json: Dict[str, Any] = {}, isSummaryRunning: bool = False):
        super().__init__()
        self.crew_instance = crew_instance  # Store the crew instance in the flow
        self.table_name = table_name
        self.summary_table_name = summary_table_name
        self.key_to_list_json = key_to_list_json
        self.index_to_row_json = index_to_row_json
        self.isSummaryRunning = False

    @start()
    async def summarize_columns_from_json(self):
        try:
            self.state.table_name = self.table_name
            self.state.summary_table_name = self.summary_table_name
            self.state.key_to_list_json = self.key_to_list_json
            self.state.index_to_row_json = self.index_to_row_json
            self.state.isSummaryRunning = True
            key_to_list_json = json.dumps(self.key_to_list_json)
            index_to_row_json = json.dumps(self.index_to_row_json)
            print("Starting summarize_columns_from_json...")
            
            # Await asynchronous crew instance kickoff
            result = await self.crew_instance.json_summarizer_agent().kickoff_async(
                inputs={
                    "key_to_list_json": key_to_list_json,
                    "index_to_row_json": index_to_row_json,
                    "table_name": self.state.table_name,
                    "summary_table_name": self.state.summary_table_name,
                    "isSummaryRunning": self.state.isSummaryRunning
                }
            )
            return result
        except Exception as e:
            print("Error:", str(e))



    async def tableSummarizerkickoff(self):
        """Async method to kickoff the summarization flow."""
        print("Starting TableSummarizerCrewFlow...")
        await self.kickoff_async()
