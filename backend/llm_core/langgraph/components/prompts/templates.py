from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.prompts import PromptTemplate


def create_augment_question_prompt(format_instructions):
    prompt_template = PromptTemplate(
        template="""
                <system>
                You are a meticulous data‑analyst agent.  
                Goal: strengthen the user’s **initial question** with facts drawn **only** from the data supplied below.

                Rules  
                1. Select *only* table rows/values that directly support or clarify the question.  
                2. **Pretend you will run a SQL query next** – keep the rows that would produce the closest possible answer and discard the rest.  
                3. Output must follow the schema exactly.
                </system>

                <user>
                Initial question:
                {question}

                Table data:
                {table_data}

                Extra context from PDF:
                {pdf_data}
                </user>

                <assistant>
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
                    You are a SQL specialist who can write SQL queries. Your job is to use the valid data points from table to write two queries.
                    Important: ensure that that you use the valid data points from the table to help you avoid mistakes in your query.

                    You must produce two queries:
                    1) An **answer_retrieval_query query** that addresses the user's question.
                    2) A **visualization query** to help visualize the results of the answer query.

                    Valid data points from the table (column & value) are {table_data_points}.
                    The users question {question}. 

                    Use the data points that can most specifically answer the question. Disregard other datas.

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
                system,
                You are an information gatherer for a pdf document. Given the following extracted parts of a PDF document (called 'summaries'), a question your task is:
                1. Gather any fundamental information that is relevant to the question (e.g., addresses, dates, values, events). 
                2. Place all relevent information in the 'response' field including useful data points
                3. Place the data points from the pdf in the 'data_points' field without any other text. Use commas to separate data points and order the data points by most specific to least specific.
                4. Return a correctly formatted python dictionary

                question: {question}
                =========
                {summaries}
                =========
                Respond using python dictionary:    "response" :  "<_START_> Your complete answer <_END_>", 
                                                    "data_points": Most relevant data points such as addresses, names, dates, emails, etc", 
                """, 
            input_variables=["summaries", "question"])


PDFAGENTPROMPTTEMPLATE_B = PromptTemplate(
    template=   """
                system,
                You are an information gatherer for a pdf document. Given the following extracted parts of a PDF document (called 'summaries'), a question and columns from a table (called 'columns') your task is:
                1. Gather any fundamental information that is relevant to the question (e.g., addresses, dates, values, events). 
                2. Look specifically for information related to each column in the table.
                3. Place all relevent information in the 'response' field including useful data points
                4. Place the data points from the pdf in the 'data_points' field without any other text. Use commas to separate data points and order the data points by most specific to least specific.
                5. Place all related column names in 'relevant_columns'. 
                6. Return a correctly formatted python dictionary

                question: {question}
                columns: {columns}
                =========
                {summaries}
                =========
                Respond using python dictionary:    "response" :  "<_START_> Your complete answer <_END_>", 
                                                    "data_points": Most relevant data points such as addresses, names, dates, emails, etc", 
                                                    "relevant_columns": Top 3 most relevant column names seperated by commas" 
                """, 
            input_variables=["summaries", "question", "columns"])

