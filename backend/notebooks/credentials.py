import json
from rich import print as rprint


def get_credentials(env_var):
    with open('credentials.json', 'r') as reader:
        credentials_dict = json.loads(reader.read())
    if env_var in credentials_dict:
        return credentials_dict[env_var]
    return None


OPENAI_API_KEY = get_credentials("OPENAI_API_KEY")
OPENAI_BASE_URL = get_credentials("OPENAI_BASE_URL")
OPENAI_MODEL_NAME = get_credentials("OPENAI_MODEL_NAME")
OPENAI_EMB_MODEL_SMALL = get_credentials("OPENAI_EMB_MODEL_SMALL")
NEO4J_URI = get_credentials("NEO4J_URI")
NEO4J_USERNAME = get_credentials("NEO4J_USERNAME")
NEO4J_PASSWORD = get_credentials("NEO4J_PASSWORD")
NEO4J_DATABASE = get_credentials("NEO4J_DATABASE")
POSTGRES_USER = get_credentials("POSTGRES_USER")
POSTGRES_PASSWORD = get_credentials("POSTGRES_PASSWORD")
POSTGRES_DB = get_credentials("POSTGRES_DB")
POSTGRES_HOST = get_credentials("POSTGRES_HOST")
POSTGRES_PORT = get_credentials("POSTGRES_PORT")

db_url = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

