import os
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from openai import AzureOpenAI
from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from sqlalchemy.exc import SQLAlchemyError
from langchain.chat_models import AzureChatOpenAI
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool

# Load environment variables
load_dotenv()

# Database connection parameters
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')

# OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Construct the connection string
connection_string = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_sql_database():
    """
    Initializes and returns an SQLDatabase instance.
    """
    try:
        db = SQLDatabase.from_uri(connection_string)
        return db
    except SQLAlchemyError as e:
        print(f"Error initializing SQLDatabase: {str(e)}")
        raise

def hello_ai():
    endpoint = os.getenv("ENDPOINT_URL", "https://nisha-m30tcbrp-westeurope.openai.azure.com/")  
    deployment = os.getenv("DEPLOYMENT_NAME", "gpt-35-turbo")  
    subscription_key = os.getenv("AZURE_OPENAI_API_KEY", "REPLACE_WITH_YOUR_KEY_VALUE_HERE")  
    
    # Initialize Azure OpenAI client with key-based authentication
    client = AzureChatOpenAI(  
        azure_endpoint=endpoint,  
        api_key=subscription_key,  
        api_version="2024-05-01-preview",
        azure_deployment=deployment,
        model_name=deployment,
        temperature=0.0 
    )  

    db = get_sql_database()

    # Here we specify the table in our question
    write_query = create_sql_query_chain(client, db)
    execute_query = QuerySQLDataBaseTool(db=db)
    chain = write_query | execute_query
    # responseA = chain.invoke({"question": "Get the column names in the usa_cars_datasets_edited table?"})

    # responseB = chain.invoke({"question": "Get upto 5 rows from the usa_cars_datasets_edited table"})

    responseC = chain.invoke({"question": "what are the different brands of cars in the usa_cars_datasets_edited table?"})



    print(responseC)


def main():
    # Initialize the database and language model
    hello_ai()

if __name__ == "__main__":
    main()
