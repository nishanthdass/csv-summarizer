from crewai_tools import NL2SQLTool, JSONSearchTool, PGSearchTool, tool, BaseTool
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
import os
from pydantic import BaseModel, Field
from typing import Type, Dict, Any
import json
from tools.custom_tool import JSONConversionTool

DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')


@CrewBase
class TableSummarizerCrew:
    """Base class for a crew agent with shared methods."""
    def __init__(self, table_name: str = ""):
        self.table_name = table_name
        self.db_uri = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        
        # Initialize tools
        self.database_tool = PGSearchTool(db_uri=self.db_uri, table_name=self.table_name)
        self.json_search_tool = JSONSearchTool()
        self.nl2sql = NL2SQLTool(db_uri=self.db_uri)
        self.json_conversion_tool = JSONConversionTool()


    @tool("JSON Conversion Tool")
    def json_conversion_tool_method(self, json_dict: Dict[str, Any]) -> str:
        """Takes a JSON object (Python dictionary) and returns a JSON-formatted string."""
        try:
            # Use the JSONConversionTool to convert the JSON object
            return self.json_conversion_tool._run({"argument": json_dict})
        except ValueError as e:
            # Handle errors from the tool gracefully
            return f"Error in JSON Conversion Tool: {str(e)}"



    @agent
    def json_summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["json_summarizer"],
            tools=[self.json_search_tool],
            llm="gpt-4o",
            function_calling_llm="gpt-4o",
            allow_delegation=True,
            verbose=True,
        )
    
    @agent
    def database_admin(self) -> Agent:
        return Agent(
            config=self.agents_config["database_admin"],
            tools=[self.nl2sql, self.json_conversion_tool],
            llm="gpt-4o",
            function_calling_llm="gpt-4o",
            allow_delegation=False,
            verbose=True,
        )
    
    @agent
    def result_responder(self) -> Agent:
        return Agent(
            config=self.agents_config["result_responder"],
            llm="gpt-4o",
            function_calling_llm="gpt-4o",
            allow_delegation=False,
            verbose=True,
        )
    
    @task
    def summarize_unordered_json(self) -> Task:
        return Task(
            config=self.tasks_config["summarize_unordered_json"],
            tools=[self.json_search_tool],
        )
    
    @task
    def summarize_ordered_json(self) -> Task:
        return Task(
            config=self.tasks_config["summarize_ordered_json"],
            tools=[self.json_search_tool],
            context=[self.summarize_unordered_json()],
        )
    
    @task
    def insert_summaries(self) -> Task:
        return Task(
            config=self.tasks_config["insert_summaries"],
            tools=[self.nl2sql, self.json_conversion_tool],
            context=[self.summarize_ordered_json()],
        )
    
    @task
    def respond_results(self) -> Task:
        return Task(
            config=self.tasks_config["respond_results"],
            context=[self.insert_summaries()],
        )

    @crew
    def json_summarizer_agent(self) -> Crew:
        """Creates the summarizer crew"""
        print("Initializing json_summarizer_agent crew...")
        return Crew(
            agents=[self.json_summarizer(), self.database_admin(), self.result_responder()],
            tasks=[self.summarize_unordered_json(), self.summarize_ordered_json(), self.insert_summaries(), self.respond_results()],
            process=Process.sequential,
            verbose=True,
        )
