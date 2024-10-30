import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST')
DB_PORT = os.getenv('POSTGRES_PORT')

def get_db_connection():
    """
    Establishes and returns a new database connection.
    """
    try:
        connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return connection
    except psycopg2.DatabaseError as e:
        print(f"Error establishing database connection: {str(e)}")
        raise

def close_db_connection(connection):
    """
    Closes the database connection.
    """
    if connection:
        connection.close()
