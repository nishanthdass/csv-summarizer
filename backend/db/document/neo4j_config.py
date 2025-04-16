import os
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

load_dotenv()


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
