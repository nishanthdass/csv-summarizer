from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


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


pdf_agent_prompt_a =  """
                Given the following extracted parts of a pdf document and a question, create a answer with references ("sources"). 
                If you don't know the answer, just share information that may be relevant to the question such as supporting details or background information that could help the user.
                Ensure that the answer starts "<_START_>" and ends with "<_END_>".
                QUESTION: {question}
                =========
                {summaries}
                =========
                answer: 
                sources:
        """
PDFAGENTPROMPTTEMPLATE_A = PromptTemplate(template=pdf_agent_prompt_a, input_variables=["summaries", "question"])

class PDF_KG_RETRIEVE_TEMPLATE(BaseModel):
    answer: str = Field(description="your answer to the question as it stands with <_START_> in the beginning and <_END_> at the end")
    data_points: str = Field(description="most relevant data points such as addresses, names, dates, emails, etc")

parser = JsonOutputParser(pydantic_object=PDF_KG_RETRIEVE_TEMPLATE)


pdf_agent_prompt_b = """
                user,
                You are an information gatherer for a pdf document. Given the following extracted parts of a PDF document (called 'summaries'), a question and columns from a table (called 'columns') your task is:
                1. Gather any fundamental information that is relevant to the question (e.g., addresses, dates, values, events). 
                2. When looking for information in the PDF, find data specific to the columns that the user asks for.
                3. Place all relevent information in the 'answer' field including useful data points.
                4. Place the most relevent data points from the pdf in the 'data_points' field without any other text. Use commas to separate data points. For example: Phone numbers, emails, addresses, dates, etc.

                question: {question}
                columns: {columns}
                =========
                {summaries}
                =========
                answer: see {format_instructions}
                """

PDFAGENTPROMPTTEMPLATE_B = PromptTemplate(template=pdf_agent_prompt_b, input_variables=["summaries", "question", "columns"], partial_variables={"format_instructions": parser.get_format_instructions()})


row_retrieval_prompt = """
                user,
                You are an information gatherer for a Table. Given the provided 'question' which is essentially a value and the extracted parts of a table called 'summaries', let me know what valuess are the closest. 
                It can be one or more. The question is vague, so you should make best effort to retreive the most similar values. You can split the 'question' into multiple parts and look through various columns. 
                For example, if you get a value like 'Bread, cheese, and milk', you can look through the columns for 'Bread', 'cheese', and 'milk' separately. 
                Return the value sand the respective column names in the 'answer' field.
                question: {question}
                =========
                {summaries}
                =========
                answer:
                sources:
        """

ROWDATAAGENTPROMPTTEMPLATE = PromptTemplate(template=row_retrieval_prompt, input_variables=["summaries", "question"])

CALLTOOLSPROMPTTEMPLATE = ChatPromptTemplate.from_messages([
        ("system",
        "You are an helpful assistant\n"
        "Answer the user's question by using your tool calls.\n\n"
        "The user's question:\n{question}"
        "Always respond in json format:\n"
        "{{\"question\": \"question for tool\", \"answer\": \"Response from tool\"}}\n\n")
    
])

DATAANALYSTPROMPTTEMPLATE = ChatPromptTemplate.from_messages([
(
        "system",
        "You are an helpful guide for a table named {table_name} and a PDF document named {pdf_name}.\n"
        "Your goal is to answer the user's question by using the information from the table and the pdf. If the qustion is not specific to the contents of the table, then find a way to use the data from the table in your answer.\n"
        "Important: Use agent_step {agent_step} to track the correct step. Always verify the current state of agent_step. Always pay attention to the agent_step in the conversation as it will guide you to the correct step.\n\n"
        "The columns names for the table are {columns_and_types}.\n\n"
        "The agent_scratchpads can be used by agents to store information from the previous step. Here is the agent_scratchpads: {agent_scratchpads}.\n\n"
        "The conversation so far:\n{user_message}\n\n"
        
        "**Steps:**\n"
        "If agent_step is 1, Identify what information is needed to answer the question (e.g., Who, Where, When). Expand or refine the question accordingly, and place your augmented question in the 'question' field.\n"
        "   - For instance, if the user asks: \"What’s a good hotel near JFK airport?\"\n"
        "     - Augment the question set to include: \"What is the address of JFK airport?\"\n"
        "       \"Which hotels are located near the address of JFK airport?\"\n"
        "       \"Are there hotels in the area of JFK airport?\"\n"
        "   - Once you have your augmented or refined set of questions, set `next_agent` to `pdf_agent`.\n\n"

        "If agent_step is 2, Identify what information from the columns of the table can aid in answering the question or strengthening the already existing answer from the previous step.\n"
        "   - Augment the question with this information. Get creative if you see that the question is not specific to the contents of the table.\n"
        "   - Place the updated question, along with any relevant information from agent_scratchpads, in the 'question' field. Set `next_agent` to `sql_agent`.\n\n"

        "If agent_step is 3, then an error was raised. Please let the user know the query that caused the error, augment the question to widen the scope of the query, and place your augmented question in the 'question' field. Set `next_agent` to `sql_agent` . You can see the error message in the agent_scratchpads field.\n\n"
        
        "If agent_step is 4 , place your answer in the 'answer' field and set `next_agent` to `__end__`. You can see the answer in the agent_scratchpads field.\n\n"

        "Always respond in json format:\n"
            "{{\"current_agent\": \"data_analyst\",\"next_agent\": \"agent name which is either pdf_agent, sql_agent or __end__\", \"question\": \"augmented question for agents and sql queries(if applicable)\", \"answer\": \" <_START_> agent_step and the Description of current step or final answer <_END_> \", \"is_multiagent\": \"True if routing to another agent, and false if routing to __end__\", \"step\": \"{agent_step}\"}}\n\n")
        ])


DATAANALYSTMULTIAGENTPROMPTTEMPLATE = ChatPromptTemplate.from_messages([
(
        "system",
        "You are an helpful guide for a table named {table_name} and a PDF document named {pdf_name}.\n"
        "Your goal is to answer the user's question by using the information from the table and the pdf.\n"
        "The agent_scratchpads contains information retreived from the pdf and the table. Here is the agent_scratchpads: {agent_scratchpads}.\n\n"

        "The question is:\n{question}\n\n"
        
        "**Steps:**\n"
        "1. Identify at a fundamental level, the information that is needed to answer the question (e.g., Who, Where, When).\n"
        "2. Look at the column names and consider if the table could give you the particular info to answer the question\n"
        "3. Augment the question by including the data points from the table(column name and value) and PDF and place your augmented question in the 'augmented_question' field.\n"
        "4. If the answer can be found via a query, then set `next_agent` to `sql_agent`, otherwise set `next_agent` to `__end__`.\n"
 

        "Always respond in json format:\n"
            "{{\"current_agent\": \"data_analyst\",\"next_agent\": \"agent name which is either sql_agent or __end__\", \"question\": \"Initial question\", \"augmented_question\": \"augmented question\", \"answer\": \" <_START_> What you think is needed to answer the question <_END_> \", \"is_multiagent\": \"True if routing to another agent, and false if routing to __end__\"}}\n\n")
        ])


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