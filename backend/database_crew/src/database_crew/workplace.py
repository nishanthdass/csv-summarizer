from dataclasses import dataclass
from qa_with_postgres.db_utility import get_summary_data
from database_crew.src.database_crew.crews.database_crew.table_sumarizer_crew import TableSummarizerCrew
from database_crew.src.database_crew.table_sumarizer_crew_flow import TableSummarizerCrewFlow
from pprint import pprint
import logging
import asyncio
import json

@dataclass
class CrewFlow:
    """Represents a Crew and its Flow within the Workplace."""
    name: str = ""
    description: str = ""
    table_name: str = ""
    crew: TableSummarizerCrew = None
    flow: TableSummarizerCrewFlow = None


class Workplace:
    """Workplace (Composition / has-a):
    Acts as a shared environment where resources and tools are available to agents. 
    It manages shared data and provides context, making it easy to expand functionality 
    without changing agent responsibilities.
    """
    
    def __init__(self, crew_flow: CrewFlow = CrewFlow()):
        self.summary_data = {}
        self.crew_flows = {}
        self.crew_flow = crew_flow

    logging.basicConfig(level=logging.DEBUG)

    async def load_summary_data(self, table_name):
        # Log loading start
        logging.debug(f"Loading summary data for {table_name}")
        
        # Load summary data for the specified table
        self.summary_data = get_summary_data(table_name=table_name + "_summary")
        
        is_summarized = self.summary_data.get('isSummarized', False)
        
        if not is_summarized:
            logging.debug(f"Summary data not available for {table_name}")
            key_to_list_json = self.summary_data.get('repacked_rows', {})
            index_to_row_json = self.summary_data.get('row_numbered_json', {})
            crew = TableSummarizerCrew(table_name=table_name)
            flow = TableSummarizerCrewFlow(crew, table_name, key_to_list_json, index_to_row_json)
            
            crew_flow = CrewFlow(
                name="SummarizerCrewFlow",
                description="Table summarizer crew and flow",
                table_name=table_name,
                crew=crew,
                flow=flow
            )
            self.add_crew_flow(crew_flow)

            # Add a log to monitor if embeddings are being created here
            logging.debug(f"Starting summarization for {table_name} with SummarizerCrewFlow")
            await self.get_crew_flow("SummarizerCrewFlow").flow.tableSummarizerkickoff()

        # Explicitly return a success message or the summary data for debugging purposes
        return {"status": "Completed"}



    def add_crew_flow(self, crew_flow: CrewFlow):
        """Add a CrewFlow instance to the workplace."""
        self.crew_flows[crew_flow.name] = crew_flow
    
    def get_crew_flow(self, name):
        """Retrieve a CrewFlow instance by name."""
        return self.crew_flows.get(name)

    def get_crew_flows(self):
        """Retrieve all CrewFlow instances."""
        return self.crew_flows
