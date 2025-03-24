from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


def create_data_analyst_prompt(format_instructions):
    prompt_template = PromptTemplate(
    template="""
            You are a data analyst that deciphers the right information to augment the initial question.
            Your goal is to augment the question with data points from the table so that a SQL query can be created to answer the question.

            You are given the following information:
            The initial question is:
            {question}

            The excerpt from the pdf is:
            {pdf_data}

            The table_data contains column names and their respective values. Here is the table_data:
            {table_data}

           Steps:
            1. Augment the question with data from both the pdf_data and the table_data to make the question more specific so that a SQL query can be created. 
            2. Use the most relevant data points in table_data to enhance the augmented question. Ignore irrelevant data points.
            2. If a part of the table_data is not in the pdf_data, then add the part of the table_data to the augmented question.

            Follow the ouptut schema below:
            {format_instructions}

            """,
                input_variables=["question", "pdf_data", "table_data"],

                partial_variables={"format_instructions": format_instructions},
            )

    return prompt_template


SQLQUERYTYPEAGENTPROMPTTEMPLATE = ChatPromptTemplate.from_messages([
            ("system",
            "Read the user's question and identify if the question is a Modify Data Query (e.g., Insert, Update, Delete, Merge, Create, Alter, Drop, Truncate, Rename, etc) or a Retrieve Query (e.g., Select, Group By, Order By, etc.)."
            "If the question is a Modify Data Query, then place 'manipulation' in the 'query_type' field."
            "If the question is a Retrieve Query, then place 'retrieval' in the 'query_type' field."
            "If the question is neither, then place 'retrieval' in the 'query_type' field."
            "Users question is: {input}"
            "Return in json format:\n"
            "{{\"query_type\": \"Either retrieval or manipulation\"}}\n\n")])


async def create_sql_retrieval_prompt(question: str, last_message: list, conversation_history: list):
    prompt_template = f"""
                    You are a SQL specialist who can write SQL queries to answer the user's question. 
                    You must produce two queries:
                    1) An **answer_retrieval_query query** that directly addresses the user's question.
                    2) A **visualization query** to help visualize the results of the answer query.

                    The user's initial question: {question}
                    The user's last message: {last_message}
                    Conversation history (if needed): {conversation_history}

                    Requirements for the answer_retrieval_query:
                    - If the answer_retrieval_query does not yield any results or fails, then set "next_agent" to "human_input". Explain why it failed in the "answer" field, provide suggestions, and wait for user response.
                    - If successful and results are more than 0, place the final tested query in "answer_retrieval_query". 
                    - Do not use "LIMIT" unless needed to answer the question.

                    Requirements for the visualization query:
                    - Include ctids in the SELECT clause.
                    - Only provide a visualization query if the answer_retrieval_query returns results (non-empty).
                    - The query should be specific to the rows that answer the question.
                    - If aggregation is needed, ensure all non-aggregated columns are in the GROUP BY clause.
                    - Typically select the whole row (ctid, *), or select just ctid plus relevant columns.

                    Label the visualization query (max 7 words), e.g. "Select all cars", "Select running totals", etc.

                    Return the following JSON exactly (fill in the fields accordingly, no extra fields):

                    {{
                    "current_agent": "sql_agent",
                    "next_agent": "__end__ if query yields non-empty results, else 'human_input'",
                    "question": "None",
                    "answer": "<_START_> Explanation of why this query is best, or explanation of failure. <_END_>",
                    "query_type": "retrieval",
                    "answer_retrieval_query": "The final tested retrieval query",
                    "visualize_retrieval_query": "Query for visualization (if any)",
                    "visualize_retrieval_label": "A label describing the visualization query"
                    }}
                    """

    return prompt_template


async def create_sql_multiagent_retrieval_prompt(question: str, table_data_points: str):
    prompt_template = f"""
                    You are a SQL specialist who can write SQL queries to answer the user's question. 
                    You must produce two queries:
                    1) An **answer_retrieval_query query** that directly addresses the user's question.
                    2) A **visualization query** to help visualize the results of the answer query.

                    The user's initial question: {question}
                    Valid Data points from the table (column & value): {table_data_points}

                    Requirements for the answer_retrieval_query:
                    - Valid data points are curated from the table data to help you avoid mistakes in your query, use them to correct your query.
                    - If the answer_retrieval_query does not yield any results or fails, then set "next_agent" to "human_input". Explain why it failed in the "answer" field, provide suggestions, and wait for user response.
                    - If successful and results are more than 0, place the final tested query in "answer_retrieval_query". 
                    - Do not use "LIMIT" unless needed to answer the question.

                    Requirements for the visualization query:
                    - Include ctids in the SELECT clause.
                    - Only provide a visualization query if the answer_retrieval_query returns results (non-empty).
                    - The query should be specific to the rows that answer the question.
                    - If aggregation is needed, ensure all non-aggregated columns are in the GROUP BY clause.
                    - Typically select the whole row (ctid, *), or select just ctid plus relevant columns.

                    Label the visualization query (max 7 words), e.g. "Select all cars", "Select running totals", etc.

                    Return the following JSON exactly (fill in the fields accordingly, no extra fields):

                    {{
                    "current_agent": "sql_agent",
                    "next_agent": "__end__ if query yields non-empty results, else 'human_input'",
                    "question": "None",
                    "answer": "<_START_> Explanation of why this query is best, or explanation of failure. <_END_>",
                    "query_type": "retrieval",
                    "answer_retrieval_query": "The final tested retrieval query",
                    "visualize_retrieval_query": "Query for visualization (if any)",
                    "visualize_retrieval_label": "A label describing the visualization query"
                    }}
                    """

    return prompt_template



async def create_sql_manipulation_prompt(question: str, last_message: list):
    prompt_template = f"""
        You are a SQL specialist who can write SQL queries to modify the database. Use delimiting or other forms of string concatenation on extracted data from the database in the perform_manipulation_query. Do not worry about being unable to modify the database yourself, focus on writing queries that the user can execute.
        Important: Verify the query is syntactically correct.

        The user's intial question is: {question}
        Users last message: {last_message}

        1   The **perform_manipulation_query** should help the user modify the data of the database. Place the final modification query in the 'perform_manipulation_query' fields.
            -   Make sure to query the database to understand the relevent data so that you can use it to formulate perform_manipulation_query. 
            -   If needed, try to make the query capable of acheiving multiple tasks in a single query. .
            -   Do not run perform_manipulation_query to alter the database, but you can run queries to look at the database. Do not let the user know that you cannot run the query to alter the database.
            -   If you created a usable perform_manipulation_query, re-check the query to make sure the syntax is correct. If the query is correct then set 'query_type' to 'manipulation' and 'next_agent' to '__end__'.
            -   Do not concern yourself with if the query is consequential or not. Your job and priority is to write a query.

        2   Label perform_manipulation_query based on its purpose (max 7 words). Place the label in the 'perform_manipulation_label' field.

        If you absolutly need more information to write the query, then set 'next_agent' to 'human_input' and in the 'answer' field provide: an explanation of what the problem is, suggestions based on the data of the table, and then wait for the user's response.

        Return in JSON format: 
        {{
            "current_agent": "sql_agent", 
            "next_agent": "__end__ or 'human_input'", 
            "question": "None",
            "answer": "<_START_> Description of created query and why its the best query to manipulate the database. If you could not create a manipulation query, explain the reason why in detail and wait for the user to respond <_END_>",
            "query_type": "manipulation",
            "perform_manipulation_query": "Query that alters the database or data",
            "perform_manipulation_label": "label that describes the perform_manipulation_query",       
        }}
        """
    
    return prompt_template




PDFAGENTPROMPTTEMPLATE_A = PromptTemplate(
    template=   """
                user,
                You are an information gatherer for a pdf document. Given the following extracted parts of a pdf document and a question:
                1. Gather any fundamental information that is relevant to the question (e.g., addresses, dates, values, events). 
                2. Place all relevant information in the 'answer' field including useful data points.
                3. Place the most relevant data points from the pdf in the 'data_points' field without any other text. Use commas to separate data points. For example: Phone numbers, emails, addresses, dates, etc.
                4. Place the most relevant page number and line number in the 'sources' field. Use commas to separate sources. For example: Page 1, Line 1, Page 2, Line 2, etc.

                If you don't know the answer, just share information that may be relevant to the question such as supporting details or background information that could help the user.

                QUESTION: {question}
                =========
                {summaries}
                =========
                Respond using JSON format: {format_instructions}
                """,
            input_variables=["summaries", "question", "format_instructions"])


PDFAGENTPROMPTTEMPLATE_B = PromptTemplate(
    template=   """
                user,
                You are an information gatherer for a pdf document. Given the following extracted parts of a PDF document (called 'summaries'), a question and columns from a table (called 'columns') your task is:
                1. Gather any fundamental information that is relevant to the question (e.g., addresses, dates, values, events). 
                2. When looking for information in the PDF, find data points specific to the columns in the table. 
                3. Rank the data points based on how they can narrow down the answer, for example: h2o is more specific than water, phone number is more specific than full name, etc
                4. Place all relevent information in the 'answer' field including useful data points. Address if the table can provide the answer if the data points are used in a database query.
                5. Place the data points from the pdf in the 'data_points' field without any other text. Use commas to separate data points and order the data points by most specific to least specific.

                question: {question}
                columns: {columns}
                =========
                {summaries}
                =========
                Respond using JSON format: {format_instructions}
                """, 
            input_variables=["summaries", "question", "columns", "format_instructions"])



























SQLAGENTMULTIAGENTPROMPTTEMPLATE = f"""
            You are a SQL expert.
            Your task is to write two new queries. One query will help answer the user's question and the other will help visualize the result. 
            Important: Do not under any circumstances place a answer query that yield an empty result in the 'answer_retrieval_query' field. You should run the answer query to check if it returns a value.
            
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
                -   Ctids should be included in the visualization query
                -   The SQL LIMIT clause should not be used unless it is relevant to answering the question more accurately.
                -   Include all non-aggregated columns in the GROUP BY clause to avoid grouping errors.
                -   Identify the most relevant columns, and choose to select the whole row (via single ctid) or the most relevant columns (ctid plus relevant columns). 
                    - For example if a users question involves selecting or viewing a home and the table is about home(including costs, location, etc.), then the visualization query should select the whole row (SELECT ctid, *). 
                    - If the question is regarding the cost of a home, then the visualization query should select the ctid and the cost column (SELECT ctid, cost).
                    - In most cases, the visualization query should select the whole row (SELECT ctid, *).
                -   Not all answers can be visualized. For example, if the user's question is "What is the average value of all items", then the visualization query should be "Select the value of all items". However if the user's question is "What is the average value of item A", then the visualization query should be "Select the value of item A".

            3 Label the query based on its purpose (max 7 words), such as 'Select all cars', 'Select running totals', etc.
        """


SQLAGENTPROMPTTEMPLATE = f"""
            Read the user's question and assess if the question is a Modify Data Query (e.g., Insert, Update, Delete, Merge, Create, Alter, Drop, Truncate, Rename, etc) or a Retrieve Query (e.g., Select, Group By, Order By, etc.).
            If the question is a Modify Data Query, then follow the steps in the Modify Data Query Steps section.
            If the question is a Retrieve Query, then follow the steps in the Retrieve Query Steps section.
            Important: Always respond in json format no matter if the question is a Modify Data Query or a Retrieve Query.
            Important: Look through all available columns for context.

            Retrieve Query Steps: If the question is Retrieve Query, then follow the 3 steps below:
                Your task is to write two new queries. One query will help answer the user's question and the other will help visualize the result. 

                    1   The **answer query** should answer the user's question. Make sure to test a few queries and study the data in the table so help the user finalize a query that returns a non-empty result. Place the final query in the 'answer_retrieval_query' field.
                        -   Consider when filtering by order that some values in the table can be null.
                        -   If the queries only returns a empty result, then place the failed query in the 'answer_retrieval_query' field and set `next_agent` to `human_input`.
                        -   Additionally, if a query fails, the agent must include all relevant information in the answer field: the failed query (verbatim), an explanation of why it failed, suggestions for an alternative query based on the insights gained, and then wait for the user's response.
                        -   If you have tested different queries to answer the question and they all return empty result, then let the user know the problem and ask them for clarification. Set next_agent to human_input and wait for the user to respond. Stop executing any processes if this condition is met.
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

            Modify Data Query: If the question is a Modify Database Query then follow the 2 steps below:
                Your task is to write a new query that modifies the database in a way that answers the user's question. This means writing queries that may use string functions, such as substring, replace, etc.
            
                    1   The **manipulation query** should help the user modify the data of the database. Make sure to test a few queries and study the data. Place the final modification query in the 'perform_manipulation_query' fields.
                        -   Make sure to test a few non-modification queries and study the source data that you use to write the modification query or the data that the modification query would.
                        -   Do not run the modification query to alter the database, but you can run queries to look at the database. Do not let the user know that you cannot run the query to alter the database.
                        -   If you were unable to create a modification query, then in the 'answer' field provide: an explanation of what the problem is, suggestions based on the data of the table, and then wait for the user's response.

                    2   Label the query based on its purpose (max 7 words). Place the label in the 'perform_manipulation_label' field.
        """



TABLEONLYPROMPTTEMPLATE = ChatPromptTemplate.from_messages([
        ("system",
        "You are the supervisor of a conversation about a table that goes by {table_name}. Never make assumptions about the content of the table based on the name of the table as a bananas column can exist in the table. Ensure that all decisions are based on facts from queries or from the other agents."
        "Your tasks are:\n\n"
        "1. If a few database queries are needed to answer the user's question, then route the question to `sql_agent`. DO not make assumptions.\n\n"
        "2. If the qustion from the user is about manipulating the data in the table, then route the question to `sql_manipulator_agent`.\n\n"
        "3. If no database query or deeper analysis is needed, set the next_agent to '__end__' and answer the question.\n\n"
        "4. If nessecary, look through {conversation_history} to look at previous messages for context.\n\n"
        "5. If the question has nothing to do with the {table_name} or if {table_name} is None table, set the next_agent to '__end__' and explain why. Never assueme anything about the table"
        "the question is unrelated.\n\n"
        "Return in json format:\n"
        "{{\"current_agent\": \"supervisor\", \"next_agent\": \"agent_name\", \"question\": \"question_text\", \"answer\": \"<_START_> answer to question or the step being taken to answer the question <_END_>\", \"answer_retrieval_query\": The previously created sql_agent query(with the ctid) or an empty string. Only use when retrieving answer from conversation_history.\", \"viewing_query_label\": The previously created sql_agent query(with the label) or an empty string.\"}}\n\n"
        "The user's last request:\n{user_message}")
    ])


TABLEANDPDFPROMPTTEMPLATE = ChatPromptTemplate.from_messages([
        ("system",
        "You are the supervisor of a conversation about a table that goes by {table_name} and a pdf that goes by {pdf_name}.\n\n"
        "Route the question to `data_analyst`\n\n"
        "{{\"current_agent\": \"supervisor\", \"next_agent\": \"agent_name\", \"question\": \"question_text\", \"answer\": \"<_START_> answer or the step being taken to answer the question <_END_>\"}}\n\n"
        "The user's last request:\n{user_message}")
    ])


PDFONLYPROMPTTEMPLATE = ChatPromptTemplate.from_messages([
        ("system",
        "You are the supervisor of a conversation about a pdf document that goes by {pdf_name}.\n\n" 
        "Never make assumptions about the content of the pdf.\n\n"
        "Simply let the user know that you can route the question to `pdf_agent` who can answer the question.\n\n"
        "Return in json format and set the next_agent to 'pdf_agent':\n"
        "{{\"current_agent\": \"supervisor\", \"next_agent\": \"agent_name\", \"question\": \"question_text\", \"answer\": \"<_START_> answer_text <_END_>\"}}\n\n"
        "The user's last request:\n{user_message}" )
    ])


NEITHERTABLEORPDFPROMPTTEMPLATE = ChatPromptTemplate.from_messages([
        ("system",
        "You are the supervisor of a conversation about the data in csv tables and pdf documentations.\n\n"
        "The user has  not selected a table or pdf yet. Never make assumptions about the content of the table or pdf.\n\n"
        "Simply let the user know that you do not have access to the tables or pdfs and ask them to select a table and/or pdf.\n\n"
        "Return in json format and set the next agent to '__end__:\n"
        "{{\"current_agent\": \"supervisor\", \"next_agent\": \"agent_name\", \"question\": \"question_text\", \"answer\": \"<_START_> answer_text <_END_>\"}}\n\n"
        "The user's last request:\n{user_message}")
    ])