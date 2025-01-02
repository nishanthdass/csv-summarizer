import json
import getpass
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector

# Load environment variables
load_dotenv()

# Database and model setup
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_NAME = os.getenv('POSTGRES_DB')
DB_HOST = os.getenv('POSTGRES_HOST')
DB_PORT = os.getenv('POSTGRES_PORT')



db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
collection_name = "step_1_ML_project_checklist"

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

# Initialize embedding model
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

# Read JSON file and parse it
with open("../raw_ML_learning_data/step_1_ML_project_checklist.json", "r") as f:
    data = json.load(f)  # Parse the JSON file into a Python dictionary or list

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=330,
    chunk_overlap=10,
    length_function=len,
    is_separator_regex=False,
)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=db_url,
    use_jsonb=True,
)

for index, item in enumerate(data):
    obj = {key: value for key, value in item.items() if key != "content"}
    entry = text_splitter.split_text(item["content"])
    doc = text_splitter.create_documents(entry, [obj])
    vector_store.add_documents(documents=doc, ids=[collection_name + str(index)])