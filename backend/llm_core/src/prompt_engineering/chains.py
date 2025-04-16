from langchain_openai import ChatOpenAI
from models.models import Route, DataAnalystResponse
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import  trim_messages
from db.document.neo4j_retrieval import kg_retrieval_window
from langchain.chains import RetrievalQAWithSourcesChain
from config import openai_var, postgres_var
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits import create_sql_agent

from models.models import MessageState
from rich import print as rprint
from llm_core.src.prompt_engineering.templates import *


async def call_sql_agent(prompt:str, state: MessageState) -> MessageState:
    """Call the SQL Agent langchain toolkit."""
    model = ChatOpenAI(model=openai_var.openai_model, stream_usage=True,temperature=0.1)
    db_for_table = SQLDatabase.from_uri(postgres_var.db_url, include_tables=[state["table_name"]])
    toolkit = SQLDatabaseToolkit(db=db_for_table, llm=model)

    sql_agent_for_table = create_sql_agent( llm=model, 
                                            toolkit=toolkit,
                                            agent_type="openai-tools",
                                            verbose=False,
                                            agent_executor_kwargs={"return_intermediate_steps": True})
    
    sql_result = await sql_agent_for_table.ainvoke(prompt)

    return sql_result


async def json_parser_prompt_chain(prompt, inputs):
    """Allow user to ask a question to the model and get a json response. User can change the model."""
    model = ChatOpenAI( model=openai_var.openai_model, 
                        max_tokens=None, 
                        stream_usage=True, 
                        temperature=0 )
    parser = JsonOutputParser(pydantic_object=Route)
    chain = prompt | model | parser
    response = await chain.ainvoke(inputs)

    return response


async def json_parser_prompt_chain_data_analyst(inputs):
    """Allow user to ask a question to the model and get a json response. User can change the model."""
    model = ChatOpenAI( model=openai_var.openai_model, 
                        max_tokens=None, 
                        stream_usage=True, 
                        temperature=0 )
    parser = JsonOutputParser(pydantic_object=DataAnalystResponse)
    prompt = create_data_analyst_prompt(format_instructions=parser.get_format_instructions())
    chain = prompt | model | parser
    response = await chain.ainvoke(inputs)

    return response

def kg_retrieval_chain(prompt, input_variables):
    chain_type_kwargs = {"prompt": prompt}

    kg_chain_window = RetrievalQAWithSourcesChain.from_chain_type(
        ChatOpenAI( temperature=0,
                    stream_usage=True,
                    openai_api_key=openai_var.openai_api_key,
                    openai_api_base=openai_var.openai_endpoint,
                    model=openai_var.openai_model,
                    verbose=True,
                    ), 
        chain_type = "stuff", 
        retriever = kg_retrieval_window(input_variables["pdf_name"]),
        chain_type_kwargs = chain_type_kwargs,
        return_source_documents = True
    )

    answer = kg_chain_window(
        input_variables,
        return_only_outputs=True,
        )

    return answer



def trimmer(state):
    """Trim messages to a maximum of 6500 tokens."""
    # rprint("Pre Trimmed Messages: ", state["messages"])
    model = ChatOpenAI(model="gpt-4o", temperature=0)

    trimmer = trim_messages(
        max_tokens=6500,
        strategy="last",
        token_counter=model,
        include_system=True,
        allow_partial=False,
        start_on="human",
    )

    trimmed_messages = trimmer.invoke(state["messages"])

    return trimmed_messages
