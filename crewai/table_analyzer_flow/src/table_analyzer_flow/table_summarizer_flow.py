
from typing import List, Dict, Any
from pydantic import BaseModel
from crewai.flow.flow import Flow, start
from crews.table_sumarizer_crew.table_sumarizer_crew import TableSummarizerCrew


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
            print("Initializing summarize_columns_from_json...")
            crew_instance = TableSummarizerCrew(table_name=self.table_name)

            # Use the crew instance to kickoff the summarizer agent
            result = await crew_instance.json_summarizer_agent().kickoff_async(inputs=inputs)

            return result
        except Exception as e:
            print("Error:", str(e))
            raise
