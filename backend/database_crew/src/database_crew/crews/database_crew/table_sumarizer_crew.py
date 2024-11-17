from crewai_tools import SerperDevTool, ScrapeWebsiteTool, NL2SQLTool, JSONSearchTool, PGSearchTool
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
import os

DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')

agents_config = "config/agents.yaml"
tasks_config = "config/tasks.yaml"

@CrewBase
class TableSummarizerCrew:
    """Base class for a crew agent with shared methods."""
    
    def __init__(self, table_name: str = ""):
        self.table_name = table_name
        self.database_tool = PGSearchTool(db_uri=f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
                                table_name=self.table_name)
        self.json_search_tool = JSONSearchTool()
        self.nl2sql = NL2SQLTool(db_uri=f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


    
    @agent
    def json_summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["json_summarizer"],
            tools=[self.json_search_tool],
        )
    
    @agent
    def database_summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["database_summarizer"],
            tools=[self.database_tool], 
        )

    @task
    def summarize_json(self) -> Task:
        return Task(
            config=self.tasks_config["summarize_json"],
            tools=[self.json_search_tool],
        )
    
    @task
    def summarize_database(self) -> Task:
        return Task(
            config=self.tasks_config["summarize_database"],
            tools=[self.database_tool],
        )
    
    @crew
    def json_summarizer_agent(self) -> Crew:
        """Creates the LatestAiDevelopment crew"""
        return Crew(
            agents=[
                self.json_summarizer(),
            ],
            tasks=[
                self.summarize_json(),
            ],
        	process=Process.sequential,
        	verbose=True,
        ) 
    
    @crew
    def database_summarizer_agent(self) -> Crew:
        """Creates the LatestAiDevelopment crew"""
        return Crew(
            agents=[
                self.database_summarizer(),
            ],
            tasks=[
                self.summarize_database(),
            ],
        	process=Process.sequential,
        	verbose=True,
        ) 
