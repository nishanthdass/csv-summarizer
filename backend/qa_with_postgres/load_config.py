# load_config.py

import os
from dotenv import load_dotenv
import yaml

load_dotenv()


class LoadConfig:
    def __init__(self) -> None:
        self.load_db()
        self.config_retrieve_assistant()

    def load_db(self):
        DB_USER = os.getenv('POSTGRES_USER')
        DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
        DB_NAME = os.getenv('POSTGRES_DB')
        DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
        DB_PORT = os.getenv('POSTGRES_PORT', '5432')
        self.connection_string = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

        # Retreive assistant.
    def config_retrieve_assistant(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL_NAME')
        self.openai_assistant_id = os.getenv('ASSISTANT_ID')
