import os
from dotenv import load_dotenv
import yaml
from pyprojroot import here
from openai import AzureOpenAI
from langchain.chat_models import AzureChatOpenAI

load_dotenv()

print("Config file path:", here("qa_with_postgres/app_config.yml"))
class LoadConfig:
    def __init__(self) -> None:
        with open(here("qa_with_postgres/app_config.yml")) as cfg:
            app_config = yaml.load(cfg, Loader=yaml.FullLoader)

        self.load_db()
        self.load_llm_configs(app_config=app_config)
        self.load_openai_models()

    def load_db(self):
        DB_USER = os.getenv('POSTGRES_USER')
        DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
        DB_NAME = os.getenv('POSTGRES_DB')
        DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
        DB_PORT = os.getenv('POSTGRES_PORT', '5432')

        self.connection_string = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    def load_llm_configs(self, app_config):
        self.model_name = os.getenv("GPT_DEPLOYMENT_NAME")
        self.agent_llm_system_role = app_config["llm_config"]["agent_llm_system_role"]
        self.rag_llm_system_role = app_config["llm_config"]["rag_llm_system_role"]
        self.temperature = app_config["llm_config"]["temperature"]
        self.embedding_model_name = os.getenv("embed_deployment_name")

    def load_openai_models(self):
        azure_openai_api_key = os.environ["AZURE_OPENAI_API_KEY"]
        azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        openai_api_version= os.environ["OPENAI_API_VERSION"]
        # This will be used for the GPT and embedding models
        self.azure_openai_client = AzureOpenAI(
            api_key=azure_openai_api_key,
            api_version=openai_api_version,
            azure_endpoint=azure_openai_endpoint
        )
        self.langchain_llm = AzureChatOpenAI(
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_api_key,
            openai_api_version=openai_api_version,
            azure_deployment=self.model_name,
            model_name=self.model_name,
            temperature=self.temperature)