import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


class LoadOpenAIConfig:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_endpoint = os.getenv('OPENAI_BASE_URL')
        self.openai_model = os.getenv('OPENAI_MODEL_NAME')
        self.openai_embedding_model = os.getenv('OPENAI_EMB_MODEL')
        self.openai_embedding_modal_small = os.getenv('OPENAI_EMB_MODEL_SMALL')
