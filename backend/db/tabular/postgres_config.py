import os
import psycopg2
from dotenv import load_dotenv

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
