from typing import List, Dict, Any
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start
from .crews.database_crew.table_sumarizer_crew import TableSummarizerCrew
from qa_with_postgres.chatbot import ChatBot
import json
import os

os.environ['OTEL_SDK_DISABLED'] = 'true'

class TableSummarizerCrewState(BaseModel):
    """State for TableSummarizerCrewFlow"""
    table_name: str = ""
    json_object: Dict[str, Any] = {}

class TableSummarizerCrewFlow(Flow[TableSummarizerCrewState]):
    def __init__(self, crew_instance: TableSummarizerCrew, table_name: str = "", json_object: Dict[str, Any] = {}):
        super().__init__()
        self.crew_instance = crew_instance  # Store the crew instance in the flow
        self.table_name = table_name
        self.json_object = json_object

    @start()
    def summarize_columns_from_json(self):
        try:
            self.state.table_name = self.table_name
            self.state.json_object = self.json_object
            json_object = json.dumps(self.json_object)
            print("JSON Object:", json_object)
            result = self.crew_instance.json_summarizer_agent().kickoff(
                inputs={
                    "json_object": json_object,
                    "table_name": self.state.table_name,
                }
            )
        except Exception as e:
            print("Error:", str(e))

        print("Result generated:", result.raw)

    @listen(summarize_columns_from_json)
    def summarize_columns_from_db(self):
        try:
            # Access the generated result here
            result = self.crew_instance.database_summarizer_agent().kickoff(
                inputs={
                    "table_name": self.state.table_name,
                }
            )
            print("Result generated:", result.raw)
        except Exception as e:
            print("Error:", str(e))


    async def tableSummarizerkickoff(self):
            """Async method to kickoff the summarization flow."""
            print("Starting TableSummarizerCrewFlow...")
            await self.kickoff_async()

