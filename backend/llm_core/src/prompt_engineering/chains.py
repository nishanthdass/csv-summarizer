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

openai_var  = LoadOpenAIConfig()
postgres_var = LoadPostgresConfig()

async def call_sql_agent(model, state: MessageState) -> MessageState:
    parser = JsonOutputParser(pydantic_object=Route)
    model = ChatOpenAI(model=model, temperature=0)
    db_for_table = SQLDatabase.from_uri(postgres_var.db_url, include_tables=[state["table_name"]])
    toolkit = SQLDatabaseToolkit(db=db_for_table, llm=model)
    sql_agent_for_table = create_sql_agent(llm=model, toolkit=toolkit, agent_type="openai-tools", verbose=False, agent_executor_kwargs={"return_intermediate_steps": True})

    question = state["question"]
    
    augmented_question = f"""Your task is to write a new query that will help answer the user's question. Only return the JSON, nothing else. Do not run any query, just write the query. Do not limit the retrieval unless it helps answer the question more accurately:\n"
                            "1. If it is an aggregate query, make sure the query yields 'ctid's that make up the result', not the Count itself \n"
                            "2. If it is not an aggregate query, modify the query to include 'ctid' dynamically in the SELECT clause along with the column name/names.\n"
                            "3. Make sure to choose the approprate column based on the table schema and the user's question.\n"
                            "4. Create a label(max 7 words) with the word 'select' that describes the query. For example, 'Select all items', 'Select the items', etc..\n\n"
                             
                            The question is: {question.content}\n\n

                            Return in JSON format: 
                                "{{\"current_agent\": \"sql_agent\", 
                                    \"next_agent\": \"sql_agent\", 
                                    \"question\": \"None\",
                                    \"answer_query\": \"Modified Query with ctid\", 
                                    \"viewing_query_label\": \"modified query label\"}}\n\n"
                            """
    
    # chain = model | sql_agent_for_table 

    # sql_result = await chain.ainvoke(augmented_question)
    # rprint(sql_result)

    sql_result = await sql_agent_for_table.ainvoke(augmented_question)

    return sql_result



async def json_parser_prompt_chain(prompt, model, inputs):
    """Allow user to ask a question to the model and get a json response. User can change the model."""
    model = ChatOpenAI(model=model, temperature=0)
    parser = JsonOutputParser(pydantic_object=Route)
    chain = prompt | model | parser
    response = await chain.ainvoke(inputs)

    return response


def kg_retrieval_chain(user_message, prompt, state):
    chain_type_kwargs = {"prompt": prompt}

    kg_chain_window = RetrievalQAWithSourcesChain.from_chain_type(
        ChatOpenAI( temperature=0,
                    openai_api_key=openai_var.openai_api_key,
                    openai_api_base=openai_var.openai_endpoint,
                    model=openai_var.openai_model
                    ), 
        chain_type = "stuff", 
        retriever = kg_retrieval_window(state["pdf_name"]),
        chain_type_kwargs = chain_type_kwargs,
        return_source_documents = True
    )

    answer = kg_chain_window(
        {"question": user_message},
        return_only_outputs=True,
        )

    return answer


def trimmer(state):
    """Trim messages to a maximum of 6500 tokens."""
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


