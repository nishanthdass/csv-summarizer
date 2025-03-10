from langchain_openai import ChatOpenAI
from models.models import Route
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import  trim_messages
from db.kg_retrieval import kg_retrieval_window
from langchain.chains import RetrievalQAWithSourcesChain
from llm_core.config.load_llm_config import LoadOpenAIConfig
from config import LoadPostgresConfig
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits import create_sql_agent
from models.models import MessageState
from rich import print as rprint
from llm_core.src.prompt_engineering.templates import SQLAGENTMULTIAGENTPROMPTTEMPLATE, SQLAGENTPROMPTTEMPLATE

openai_var  = LoadOpenAIConfig()
postgres_var = LoadPostgresConfig()

async def call_sql_agent(model, state: MessageState) -> MessageState:
    model = ChatOpenAI(model=model, stream_usage=True,temperature=0.1)
    db_for_table = SQLDatabase.from_uri(postgres_var.db_url, include_tables=[state["table_name"]])
    toolkit = SQLDatabaseToolkit(db=db_for_table, llm=model)
    sql_agent_for_table = create_sql_agent( llm=model, 
                                            toolkit=toolkit,
                                            agent_type="openai-tools",
                                            verbose=False,
                                            agent_executor_kwargs={"return_intermediate_steps": True})
    
    trimmed_messages = trimmer(state)
    question = state["question"]
    # rprint("Question: ", question.content)
    # rprint("Users last message: ", trimmed_messages[-1])

    if state["agent_step"] > 0:
        rprint("Agent Step: ", state["agent_step"])
        rprint("Trimmed Messages if interupted by human unsliced: ", trimmed_messages)
        trimmed_messages = trimmed_messages[len(trimmed_messages) - state["agent_step"]:]
        rprint("Trimmed messages if interupted by human: ", trimmed_messages)
    # else:
    #     rprint("Trimmed Messages: ", trimmed_messages)

    augmented_question = f"""
        You are a SQL specialist who can write SQL queries to answer the user's question. Sometimes your query does not work and the user will need to provide you with additional information.

        Look through the prior conversation history for context and answer the user's question.
        The user's intial question is: {question.content}
        Users last message: {trimmed_messages[-1]}
        The conversation history is: {trimmed_messages}


        Return in JSON format: 
        "{{\"current_agent\": \"sql_agent\", 
            \"next_agent\": \"human_input(if the query fails) or __end__\", 
            \"question\": \"None\",
            \"answer\": \"<_START_>  Description of created query and why its the best query to answer the question. If the query fails, then share the answer query that failed verbatim in the answer, explain the reason why it failed, provide suggestions for a different query and wait for the user to respond<_END_>\",
            \"query_type\": \"Either retrieval, manipulation, permission or transaction\",
            \"answer_retrieval_query\": \"Either a Failed Query, Retrieval Query that answers the question and is successfully tested, Manipulation Query that alters the database, Permission Query that grants or revokes permissions, or Transaction Query that starts, commits, or rollbacks a transaction.\",
            \"visualize_retrieval_query\": \"If Retrieval Query, then insert Query that visualizes the answer (has ctids), else empty string\",
            \"visualize_retrieval_label\": \"If Retrieval Query, then insert the label that describes the visualize_retrieval_query, else empty string \",
            \"perform_manipulation_query\": \"If Manipulation Query, then insert Query that alters the database or database, else empty string\",
            \"perform_manipulation_label\": \"If Manipulation Query, then insert the label that describes the perform_manipulation_query, else empty string\",
            }}\n\n"
        """
    

    if state["is_multiagent"] is True:
        prompt = SQLAGENTMULTIAGENTPROMPTTEMPLATE + augmented_question
    else:
        prompt = augmented_question + SQLAGENTPROMPTTEMPLATE
        
    sql_result = await sql_agent_for_table.ainvoke(prompt)

    return sql_result

async def call_sql_manipulator_agent(model, state: MessageState) -> MessageState:
    model = ChatOpenAI(model=model, stream_usage=True,temperature=0.0)
    db_for_table = SQLDatabase.from_uri(postgres_var.db_url, include_tables=[state["table_name"]])
    toolkit = SQLDatabaseToolkit(db=db_for_table, llm=model)
    sql_agent_for_table = create_sql_agent( llm=model, 
                                            toolkit=toolkit,
                                            agent_type="openai-tools",
                                            verbose=False,
                                            agent_executor_kwargs={"return_intermediate_steps": True})

    question = state["question"]

    prompt = f"""
        You are a SQL specialist who can write SQL queries to make changes to the database.
        You do not need to run the query to alter the database, but you can run queries to look at the database before writing the final query. You are given the user's question and the database schema.
        Make sure to query the database to understand the relevent data before adding new data to the database. Try to make the query general enough to be able to answer any question about the table.

        The user's question is: {question.content}


        Return in JSON format: 
        "{{\"current_agent\": \"sql_agent\", 
            \"next_agent\": \"sql_agent\", 
            \"question\": \"None\",
            \"answer\": \"<_START_> Description of created query, or issues with the question<_END_>\",
            \"query_type\": \"Either retrieval, manipulation, permission or transaction\",
            \"answer_query\": \"Query needed to alter the database\",
            \"viewing_query_label\": \"Label that describes the query needed to alter the database\",
            \"status\": \"success if query is successfully created, else fail\"}}\n\n"
        """
    

    sql_result = await sql_agent_for_table.ainvoke(prompt)

    return sql_result



async def json_parser_prompt_chain(prompt, model, inputs):
    """Allow user to ask a question to the model and get a json response. User can change the model."""
    model = ChatOpenAI(model=model, max_tokens=None, stream_usage=True, temperature=0)
    parser = JsonOutputParser(pydantic_object=Route)
    chain = prompt | model | parser
    response = await chain.ainvoke(inputs)

    return response


def kg_retrieval_chain(user_message, prompt, state):
    chain_type_kwargs = {"prompt": prompt}

    kg_chain_window = RetrievalQAWithSourcesChain.from_chain_type(
        ChatOpenAI( temperature=0,
                    stream_usage=True,
                    openai_api_key=openai_var.openai_api_key,
                    openai_api_base=openai_var.openai_endpoint,
                    model=openai_var.openai_model
                    ), 
        chain_type = "stuff", 
        retriever = kg_retrieval_window(state["pdf_name"]),
        chain_type_kwargs = chain_type_kwargs,
    
        return_source_documents = True
    )

    # kg_chain_column_window = RetrievalQAWithSourcesChain.from_chain_type(
    #     ChatOpenAI( temperature=0,
    #                 stream_usage=True,
    #                 openai_api_key=openai_var.openai_api_key,
    #                 openai_api_base=openai_var.openai_endpoint,
    #                 model=openai_var.openai_model
    #                 ), 
    #     chain_type = "stuff", 
    #     retriever = kg_column_retrieval_window(state["pdf_name"]),
    #     chain_type_kwargs = chain_type_kwargs,
    
    #     return_source_documents = True
    # )

    answer = kg_chain_window(
        {"question": user_message},
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


