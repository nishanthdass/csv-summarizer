import os
import psycopg2
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph


load_dotenv()

class LoadPostgresConfig:
    """
    Configuration class for PostgreSQL database.
    """
    def __init__(self):
        """
        Initializes the configuration for PostgreSQL database.
        """
        self.db_user = os.getenv('POSTGRES_USER')
        self.db_password = os.getenv('POSTGRES_PASSWORD')
        self.db_name = os.getenv('POSTGRES_DB')
        self.db_host = os.getenv('POSTGRES_HOST')
        self.db_port = os.getenv('POSTGRES_PORT')
        self.db_url = f"postgresql+psycopg2://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        self.engine = None
        self.session = None

    def get_db_connection(self):
        """
        Establishes and returns a new database connection.
        """
        try:
            connection = psycopg2.connect(
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port
            )
            return connection
        except psycopg2.DatabaseError as e:
            print(f"Error establishing database connection: {str(e)}")
            raise
        
    def get_db_url(self):
        """
        Returns the database connection URL.
        """
        return self.db_url

    def close_db_connection(self, connection):
        """
        Closes the database connection.
        """
        if connection:
            connection.close()


class LoadNeo4jConfig:
    """
    Configuration class for Neo4j database.
    """
    def __init__(self):
        """
        Initializes the configuration for Neo4j database.
        """
        self.neo4j_uri = os.getenv('NEO4J_URI')
        self.neo4j_user = os.getenv('NEO4J_USERNAME')
        self.neo4j_password = os.getenv('NEO4J_PASSWORD')
        self.neo4j_db = os.getenv('NEO4J_DATABASE')

    def get_neo4j_connection(self):
        """
        Establishes and returns a new Neo4j database connection.
        """
        return Neo4jGraph(
            url=self.neo4j_uri, username=self.neo4j_user, password=self.neo4j_password, database=self.neo4j_db
        )
    
    def get_uri(self):
        """Returns the Neo4j connection URI."""
        return self.neo4j_uri
    
    def get_user(self):
        """Returns the Neo4j username."""
        return self.neo4j_user
    
    def get_password(self):
        """Returns the Neo4j password."""
        return self.neo4j_password


class LoadOpenAIConfig:
    """
    Configuration class for OpenAI API.
    """
    def __init__(self):
        """
        Initializes the configuration for OpenAI API.
        """
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_endpoint = os.getenv('OPENAI_BASE_URL')
        self.openai_model = os.getenv('OPENAI_MODEL_NAME')
        self.openai_embedding_model = os.getenv('OPENAI_EMB_MODEL')
        self.openai_embedding_modal_small = os.getenv('OPENAI_EMB_MODEL_SMALL')


openai_var  = LoadOpenAIConfig()
postgres_var = LoadPostgresConfig()
neo4j_var = LoadNeo4jConfig()