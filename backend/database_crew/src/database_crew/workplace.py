from dataclasses import dataclass
from qa_with_postgres.db_utility import get_summary_data
from database_crew.src.database_crew.crews.database_crew.table_sumarizer_crew import TableSummarizerCrew
from database_crew.src.database_crew.table_sumarizer_crew_flow import TableSummarizerCrewFlow
from pprint import pprint
import threading
import time

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
        self.threads = {}  # Store active threads by crew name
        self.stop_flags = {}  # Store stop flags for each crew thread

    def build_crew_flow(self, table_name: str) -> CrewFlow:
        """Builds and returns a CrewFlow instance for the given table name."""
        summary_table_name = table_name + "_summary"
        key_to_list_json = self.summary_data.get('repacked_rows', {})
        index_to_row_json = self.summary_data.get('row_numbered_json', {})
        
        crew = TableSummarizerCrew(table_name=table_name.lower())
        flow = TableSummarizerCrewFlow(
            crew, 
            table_name.lower(), 
            summary_table_name.lower(), 
            key_to_list_json, 
            index_to_row_json
        )
        
        return CrewFlow(
            name="SummarizerCrewFlow",
            description="Table summarizer crew and flow",
            table_name=table_name,
            crew=crew,
            flow=flow
        )

    def run_crew_in_thread(self, crew_flow_name):
        """Run the crew flow in a separate thread."""
        crew_flow = self.get_crew_flow(crew_flow_name)
        if not crew_flow:
            raise ValueError(f"CrewFlow {crew_flow_name} does not exist.")

        # Define a stop flag for the thread
        stop_flag = threading.Event()
        self.stop_flags[crew_flow_name] = stop_flag

        def thread_target():
            print(f"Starting crew flow: {crew_flow_name}")
            try:
                while not stop_flag.is_set():
                    # Simulate crew execution with periodic checks for the stop flag
                    time.sleep(1)  # Replace with actual crew logic
                    print(f"Crew flow {crew_flow_name} is running...")
            except Exception as e:
                print(f"Error in crew flow {crew_flow_name}: {e}")
            finally:
                print(f"Crew flow {crew_flow_name} stopped.")

        # Start the thread
        thread = threading.Thread(target=thread_target, daemon=True)
        self.threads[crew_flow_name] = thread
        thread.start()

    def stop_crew_thread(self, crew_flow_name):
        """Signal the thread to stop."""
        stop_flag = self.stop_flags.get(crew_flow_name)
        thread = self.threads.get(crew_flow_name)

        if stop_flag:
            stop_flag.set()  # Signal the thread to stop
        if thread and thread.is_alive():
            thread.join()  # Wait for the thread to finish

        # Clean up
        self.threads.pop(crew_flow_name, None)
        self.stop_flags.pop(crew_flow_name, None)
        print(f"Stopped crew flow thread: {crew_flow_name}")

    def add_crew_flow(self, crew_flow: CrewFlow):
        """Add a CrewFlow instance to the workplace."""
        self.crew_flows[crew_flow.name] = crew_flow

    def get_crew_flow(self, name):
        """Retrieve a CrewFlow instance by name."""
        return self.crew_flows.get(name)

    def get_crew_flows(self):
        """Retrieve all CrewFlow instances."""
        return self.crew_flows
    

    async def load_summary_data(self, table_name: str):
        """Loads summary data and starts the summarizer crew flow if needed."""
        # Load summary data for the specified table
        self.summary_data = get_summary_data(table_name=table_name.lower() + "_summary")
        
        is_summarized = self.summary_data.get('isSummarized', False)
        
        if not is_summarized:
            # Build the CrewFlow
            crew_flow = self.build_crew_flow(table_name)
            self.add_crew_flow(crew_flow)

            # Add a log to monitor if embeddings are being created here
            result = await crew_flow.flow.tableSummarizerkickoff()
            return result
