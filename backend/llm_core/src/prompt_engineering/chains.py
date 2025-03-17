from langchain_openai import ChatOpenAI
from models.models import Route
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import  trim_messages
from db.kg_retrieval import kg_retrieval_window, kg_column_retrieval_window
from langchain.chains import RetrievalQAWithSourcesChain, LLMChain
from llm_core.config.load_llm_config import LoadOpenAIConfig
from config import LoadPostgresConfig
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits import create_sql_agent
from models.models import MessageState
from rich import print as rprint
from llm_core.src.prompt_engineering.templates import SQLAGENTMULTIAGENTPROMPTTEMPLATE, SQLAGENTPROMPTTEMPLATE
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
import logging
import json
import re


openai_var  = LoadOpenAIConfig()
postgres_var = LoadPostgresConfig()

async def find_query_type(question: str):
    """Pass initial prompt to LLM chain to determine query type."""

    prompt = ChatPromptTemplate.from_messages([
            ("system",
            "Read the user's question and identify if the question is a Modify Data Query (e.g., Insert, Update, Delete, Merge, Create, Alter, Drop, Truncate, Rename, etc) or a Retrieve Query (e.g., Select, Group By, Order By, etc.)."
            "If the question is a Modify Data Query, then place 'manipulation' in the 'query_type' field."
            "If the question is a Retrieve Query, then place 'retrieval' in the 'query_type' field."
            "If the question is neither, then place 'retrieval' in the 'query_type' field."
            "Users question is: {question}"
            "Return in json format:\n"
            "{{\"query_type\": \"Either retrieval or manipulation\"}}\n\n")])
    
    inputs = {"question": question}

    model = "gpt-4o"

    try:
        response = await json_parser_prompt_chain(prompt, model, inputs)
    except Exception as e:
        logging.error(f"Error invoking chain: {e}")
        response = None

    if type(response) != dict:
        match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        
        if match:
            json_str = match.group(1).strip()  # Extract JSON part only
            response = json.loads(json_str)
        else:
            rprint("No valid JSON found in find_query_type")

    return response




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
    # rprint("State: ", state)
    question = state["question"]
    if 'augmented_question' in state:
        augmented_question = state["augmented_question"]
    else:
        augmented_question = None

    if state["agent_step"] > 0:
        # rprint("agent_step > 0 Agent Step: ", state["agent_step"])
        # rprint("agent_step > 0 Unsliced: ", trimmed_messages)
        trimmed_messages = trimmed_messages[len(trimmed_messages) - (int(state["agent_step"])-1):]
        # rprint("agent_step > 0, Users last message: ", trimmed_messages[-1])
        # rprint("agent_step > 0, Conversation history: ", trimmed_messages)
    # else:
    #     rprint("trimmed_messages: ", trimmed_messages)
    #     rprint("agent_step == 0, Question: ", question.content)
    #     rprint("agent_step == 0, Agent Step: ", state["agent_step"])
    #     rprint("agent_step == 0, Users last message: ", trimmed_messages[-1])
    #     rprint("agent_step == 0, Conversation history: ", trimmed_messages)

    retrieval_question = f"""
        You are a SQL specialist who can write SQL queries to answer the user's question. Your task is to write two new queries. One query will help answer the user's question and the other will help visualize the result.
        Important: If the user changes the subject of the conversation, then place '__reevaluate__' in the 'query_type' field and next_agent to '__end__'.
        Important: Always respond in json format.
        Important: Look through all available columns for context.
        Important: Do not make assumptions about the results of the query, always check the results for accuracy and completeness.

        Look through the prior conversation history for context and answer the user's question.
        The user's intial question is: {question.content}
        Users last message: {trimmed_messages[-1]}
        Agent Step: {state["agent_step"]}
        Conversation history is: {trimmed_messages}

        1   The **answer query** should answer the user's question. Make sure to test a few queries and study the data in the table so help the user finalize a query that returns a non-empty result. Place the final query in the 'answer_retrieval_query' field.
            -   Consider when filtering by order that some values in the table can be null.
            -   If the user's question will yield a large number of results, then avoid using the SQL LIMIT clause and avoid running query for testing. Simply check if the table has the necessary columns and rows that make up the answer.

        2 The **visualization query** should help visualize the answer.
            -   If the answer query returns empty results, then leave the visualization query blank.
            -   Ctids should be included in the visualization query
            -   The visualization query should try to be specific to the rows that make up the answer
            -   The SQL LIMIT clause should not be used unless it is relevant to answering the question more accurately.
            -   Include all non-aggregated columns in the GROUP BY clause to avoid grouping errors.
            -   Identify the most relevant columns, and choose to select the whole row (via single ctid) or the most relevant columns (ctid plus relevant columns). 
                - For example if a users question involves selecting or viewing a home and the table is about home(including costs, location, etc.), then the visualization query should select the whole row (SELECT ctid, *). 
                - If the question is regarding the cost of a home, then the visualization query should select the ctid and the cost column (SELECT ctid, cost).
                - In most cases, the visualization query should select the whole row (SELECT ctid, *).
            -   Not all answers can be visualized. For example, if the user's question is "What is the average value of all items", then the visualization query should be "Select the value of all items". However if the user's question is "What is the average value of item A", then the visualization query should be "Select the value of item A".

        3 Label the query based on its purpose (max 7 words), such as 'Select all cars', 'Select running totals', etc.
            -   If the answer query returns empty results, then leave the visualization query blank.

        IMPORTANT: In the event that a query Fails, yields no results or if you need more information please respond with the following:
            -   Set `next_agent` to `human_input`.
            -   Place the failed query in the 'answer_retrieval_query' field
            -   Include in the 'answer' field: the failed query (verbatim), suggestions for an alternative query based on data from the SQL function calls, and then wait for the user's response.

        Return in JSON format: 
            "{{\"current_agent\": \"sql_agent\", 
                \"next_agent\": \"__end__\", 
                \"question\": \"None\",
                \"answer\": \"<_START_>  Description of created query and why its the best query to answer the question. If the query fails, then share the answer query that failed verbatim in the answer, explain the reason why it failed, provide suggestions for a different query and wait for the user to respond<_END_>\",
                \"query_type\": \"retrieval or __reevaluate__(if the user changes the subject of the conversation)\",
                \"answer_retrieval_query\": \"Either a Failed Query or a Retrieval Query that answers the question and is successfully tested\",
                \"visualize_retrieval_query\": \"Query that visualizes the answer (has ctids) \",
                \"visualize_retrieval_label\": \"Insert the label that describes the visualize_retrieval_query \",
                }}\n\n"
        """
    
    retrieval_question_multi = f"""
        You are a SQL specialist who can write SQL queries to answer the user's question. Your task is to write two new queries. One query will help answer the user's question and the other will help visualize the result.
        Important: Only provide answer queries that yield actual results. Keep in mind that an empty query response does not get flagged as a response. I need actual values in my response.
        Important: Look through all available columns for context.
        Important: Do not make assumptions about the results of the query, always check the results for accuracy and completeness.

        Look through the prior conversation history for context and answer the user's question.
        The user's question is: {augmented_question}

        1   The **answer query** should answer the user's question. 
                A.  Test the query to ensure it returns a value that is not empty, otherwise modify the answer query and try again until it yields a non-empty result.

                B.  Base all query arguments on the information in the user’s question.
                    -   Avoid generating your own data for the WHERE clause, but it is fine to manipulate the range slightly to widen the results.
                    -   Avoid vague or overly broad filters that return irrelevant results.
                    
                C.  Iterate from more specific to less specific queries.
                    -   If a user specifies a single ZIP code (e.g., 10023), consider expanding it into a range (e.g., 10020-10025) if the initial query fails to return results.
                    -   Similarly, if a user references a numeric value like “40 degrees,” expand it to a small range (e.g., 39–41) if necessary.
                    
                D.  Once tested, place the query in the 'answer_retrieval_query' field.

        2 The **visualization query** should help visualize the answer.
            -   If the answer query returns empty results, then leave the visualization query blank.
            -   Ctids should be included in the visualization query
            -   The visualization query should try to be specific to the rows that make up the answer
            -   The SQL LIMIT clause should not be used unless it is relevant to answering the question more accurately.
            -   Include all non-aggregated columns in the GROUP BY clause to avoid grouping errors.
            -   Identify the most relevant columns, and choose to select the whole row (via single ctid) or the most relevant columns (ctid plus relevant columns). 
                - For example if a users question involves selecting or viewing a home and the table is about home(including costs, location, etc.), then the visualization query should select the whole row (SELECT ctid, *). 
                - If the question is regarding the cost of a home, then the visualization query should select the ctid and the cost column (SELECT ctid, cost).
                - In most cases, the visualization query should select the whole row (SELECT ctid, *).
            -   Not all answers can be visualized. For example, if the user's question is "What is the average value of all items", then the visualization query should be "Select the value of all items". However if the user's question is "What is the average value of item A", then the visualization query should be "Select the value of item A".

        3 Label the query based on its purpose (max 7 words), such as 'Select all cars', 'Select running totals', etc.
            -   If the answer query returns empty results, then leave the visualization query blank.

        Return in JSON format: 
            "{{\"current_agent\": \"sql_agent\", 
                \"next_agent\": \"__end__\", 
                \"question\": \"None\",
                \"answer\": \"<_START_>  Description of created query and why its the best query to answer the question. If the query fails, then share the answer query that failed verbatim in the answer, explain the reason why it failed, provide suggestions for a different query and wait for the user to respond<_END_>\",
                \"query_type\": \"retrieval or __reevaluate__(if the user changes the subject of the conversation)\",
                \"answer_retrieval_query\": \"Either a Failed Query or a Retrieval Query that answers the question and is successfully tested\",
                \"visualize_retrieval_query\": \"Query that visualizes the answer (has ctids) \",
                \"visualize_retrieval_label\": \"Insert the label that describes the visualize_retrieval_query \",
                }}\n\n"
        """
    
    manipulation_question = f"""
        You are a SQL specialist who can write SQL queries to modify the database. Do not worry about being unable to modify the database yourself, focus on writing queries that the user can execute.
        Important: If you are to generate a query, then you need to verify the query is syntactically correct.
        Important: Always respond in json format.
        Important: Look through all available columns for context.

        Look through the prior conversation history for context and answer the user's question.
        The user's intial question is: {question.content}
        Users last message: {trimmed_messages[-1]}
        Agent Step: {state["agent_step"]}

        Your task is to write a SQL query that the user can execute. This means writing syntactically correct queries that modify the database, not running the query yourself.
        1   The **manipulation query** should help the user modify the data of the database. Make sure to test a few queries and study the data. Place the final modification query in the 'perform_manipulation_query' fields.
            -   Make sure to query the database to understand the relevent data before adding new data to the database. 
            -   If needed, try to make the query capable of acheiving multiple tasks in a single query.
            -   Do not run the manipulation query to alter the database, but you can run queries to look at the database. Do not let the user know that you cannot run the query to alter the database.
            -   If you created a usable manipulation query, re-check the query to make sure the syntax is correct. If the query is correct then set 'query_type' to 'manipulation' and 'next_agent' to '__end__'.
            -   Do not concern yourself with if the query is consequential or not. Your job and priority is to write a query.

        2   Label the query based on its purpose (max 7 words). Place the label in the 'perform_manipulation_label' field.

        If you absolutly need more information to write the query, then set 'next_agent' to 'human_input' and in the 'answer' field provide: an explanation of what the problem is, suggestions based on the data of the table, and then wait for the user's response.

        Return in JSON format: 
        "{{\"current_agent\": \"sql_agent\", 
            \"next_agent\": \"__end__\", 
            \"question\": \"None\",
            \"answer\": \"<_START_>  Description of created query and why its the best query to manipulate the database. If you could not create a manipulation query, explain the reason why in detail and wait for the user to respond<_END_>\",
            \"query_type\": \"Either manipulation or __reevaluate__(if user changes the subject of the conversation)\",
            \"perform_manipulation_query\": \"Query that alters the database or data\",
            \"perform_manipulation_label\": \"label that describes the perform_manipulation_query\",
            }}\n\n"
        """
    
    if state["query_type"] == "retrieval":
        if state["is_multiagent"] is True:
            prompt = retrieval_question_multi
            # rprint("Prompt: ", prompt)
        else:
            prompt = retrieval_question
    elif state["query_type"] == "manipulation":
        prompt = manipulation_question
        
    sql_result = await sql_agent_for_table.ainvoke(prompt)

    # rprint("SQL Agent Result: ", sql_result)

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
            \"answer_retrieval_query\": \"Query needed to alter the database\",
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

async def json_parser_prompt_chain_with_tools(prompt, model, inputs, tools, config):
    """Allow user to ask a question to the model and get a json response. User can change the model."""
    model = ChatOpenAI(model=model, max_tokens=None, stream_usage=True, temperature=0)
    model.bind_tools(tools)
    parser = JsonOutputParser(pydantic_object=Route)
    chain = prompt | model | parser
    response = await chain.ainvoke(inputs, config)

    return response


def kg_retrieval_chain(user_message, prompt, state):
    chain_type_kwargs = {"prompt": prompt}
    rprint("kg_retrieval_chain: Function started")
    rprint("chain_type_kwargs: ", chain_type_kwargs)


    kg_chain_window = RetrievalQAWithSourcesChain.from_chain_type(
        ChatOpenAI( temperature=0,
                    stream_usage=True,
                    openai_api_key=openai_var.openai_api_key,
                    openai_api_base=openai_var.openai_endpoint,
                    model=openai_var.openai_model,
                    verbose=True
                    ), 
        chain_type = "stuff", 
        retriever = kg_retrieval_window(state["pdf_name"]),
        chain_type_kwargs = chain_type_kwargs,
    
        return_source_documents = True
    )
    rprint("user_message: ", user_message)
    answer = kg_chain_window(
        {"question": user_message,
         "columns": str(state["columns_and_types"])},
        return_only_outputs=True,
        )
    
    return answer


def kg_retrieval_column_chain(user_message, prompt, state):
    rprint("kg_retrieval_column_chain: Function started")
    chain_type_kwargs = {"prompt": prompt}
    rprint("chain_type_kwargs: ", chain_type_kwargs)
    
    try:
        rprint("Initializing RetrievalQAWithSourcesChain")
        kg_chain_window = RetrievalQAWithSourcesChain.from_chain_type(
            ChatOpenAI(
                temperature=0,
                stream_usage=True,
                openai_api_key=openai_var.openai_api_key,
                openai_api_base=openai_var.openai_endpoint,
                model=openai_var.openai_model,
                verbose=True
            ), 
            chain_type="stuff", 
            retriever=kg_column_retrieval_window(state["table_name"]),
            chain_type_kwargs=chain_type_kwargs,
            return_source_documents=True
        )
        rprint("kg_chain_window successfully created")
    except Exception as e:
        rprint(f"Error creating kg_chain_window: {e}")
        return {"error": f"Chain creation failed: {str(e)}"}

    try:
        rprint("Calling kg_chain_window...")
        rprint("user_message: ", user_message)
        answer = kg_chain_window(
            {"question": user_message,
            "columns": str(state["columns_and_types"])},
            return_only_outputs=True,
            )
        rprint("kg_chain_window executed successfully")
    except Exception as e:
        rprint(f"Error executing kg_chain_window: {e}")
        return {"error": f"Chain execution failed: {str(e)}"}
    
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
