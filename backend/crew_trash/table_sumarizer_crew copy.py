# from crewai_tools import SerperDevTool, ScrapeWebsiteTool, NL2SQLTool
# from crewai import Agent, Crew, Process, Task
# from crewai.project import CrewBase, agent, crew, task
# from database_crew.src.database_crew.crews.database_crew.database_query_tool import ChatBotTool
# import os



# class TableSummarizerCrew:
#     """Base class for a crew agent with shared methods."""
    
#     def __init__(self, name, workplace):
#         self.name = name
#         self.description = ""
#         self.workplace = workplace
#         self.agents = []
#         self.tasks = []
        
# @CrewBase
# class TableSummarizerCrew:
#     """Database Crew"""

#     agents_config = 'config/agents.yaml'
#     tasks_config = 'config/tasks.yaml'

#     DB_USER = os.getenv('POSTGRES_USER')
#     DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
#     DB_NAME = os.getenv('POSTGRES_DB')
#     DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
#     DB_PORT = os.getenv('POSTGRES_PORT', '5432')

#     nl2sql = NL2SQLTool(db_uri=f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

#     @agent
#     def question_validator(self) -> Agent:
#         return Agent(
#             config=self.agents_config['question_validator'],
#             tools=[self.database_query_tool],  # Remove parentheses here
#         )

#     @agent
#     def task_coordinator(self) -> Agent:
#         return Agent(
#             config=self.agents_config['task_coordinator'],
#         )

#     @agent
#     def query_generation_agent(self) -> Agent:
#         return Agent(
#             config=self.agents_config['query_generation_agent'],
#             tools=[self.nl2sql]
#         )

#     @agent
#     def analytics_agent(self) -> Agent:
#         return Agent(
#             config=self.agents_config['analytics_agent'],
#             tools=[self.nl2sql],
#         )

#     @agent
#     def summarization_agent(self) -> Agent:
#         return Agent(
#             config=self.agents_config['summarization_agent'],
#         )

#     @agent
#     def answer_evaluation_agent(self) -> Agent:
#         return Agent(
#             config=self.agents_config['answer_evaluation_agent'],
#         )

#     @task
#     def retrieve_columns(self) -> Task:
#         return Task(
#             config=self.tasks_config['retrieve_columns'],
#             tools=[self.database_query_tool],  # Remove parentheses here
#         )

#     @task
#     def rephrase_and_check_data(self) -> Task:
#         return Task(
#             config=self.tasks_config['rephrase_and_check_data'],
#             tools=[self.database_query_tool],  # Remove parentheses here
#         )

#     @task
#     def answer_and_classify_question(self) -> Task:
#         return Task(
#             config=self.tasks_config['answer_and_classify_question'],
#             tools=[self.database_query_tool],  # Remove parentheses here
#         )

#     @task
#     def coordinate_task(self) -> Task:
#         return Task(
#             config=self.tasks_config['coordinate_task'],
#         )

#     @task
#     def query_data(self) -> Task:
#         return Task(
#             config=self.tasks_config['query_data'],
#         )

#     @task
#     def analyze_data(self) -> Task:
#         return Task(
#             config=self.tasks_config['analyze_data'],
#         )

#     @task
#     def summarize_data(self) -> Task:
#         return Task(
#             config=self.tasks_config['summarize_data'],
#         )

#     @task
#     def evaluate_answer(self) -> Task:
#         return Task(
#             config=self.tasks_config['evaluate_answer'],
#         )

#     @crew
#     def task_crew(self) -> Crew:
#         """Creates the Task Crew"""

#         return Crew(
#             agents=[
#                 self.question_validator(),
#                 # self.task_coordinator(),
#             ],
#             tasks=[
#                 self.retrieve_columns(),
#                 self.rephrase_and_check_data(),
#                 self.answer_and_classify_question(),
#                 # self.coordinate_task(),
#             ],
#             process=Process.sequential,
#             verbose=True
#         )

#     # @crew   
#     # def worker_crew(self) -> Crew:
#     #     """Creates the Research Crew"""
#     #     manager_agent = Agent(
#     #         config=self.agents_config['manager_agent'],  
#     #         allow_delegation = True              
#     #     )

#     #     return Crew(
#     #         agents=[
#     #             self.query_generation_agent(),
#     #             self.analytics_agent(),
#     #             self.summarization_agent(),
#     #             self.answer_evaluation_agent(),
#     #         ],
#     #         tasks=[
#     #             self.query_data(),
#     #             self.analyze_data(),
#     #             self.summarize_data(),
#     #             self.evaluate_answer(),
#     #         ],
#     #         process=Process.hierarchical,
#     #         manager_agent=manager_agent,
#     #         verbose=True
#     #     )
