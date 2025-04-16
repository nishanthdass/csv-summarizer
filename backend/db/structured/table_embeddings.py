from config import postgres_var
from llm_core.src.utils.embedding_utils import get_embedder
from db.structured.postgres_utilities import fetch_all_rows_from_table, create_langchain_docs_from_rows, get_all_columns_and_types
from langchain_core.documents import Document
from langchain_postgres import PGVector



def create_embeddings_of_table_rows(table_name: str, docs: list):
    """
    Creates embeddings of the rows in the table. To be used for similarity search of table rows.
    """
    try:
        collection_name = table_name + "_collection"
        vector_store = PGVector(
            embeddings=get_embedder(512),
            collection_name=collection_name,
            connection=postgres_var.get_db_url(),
        )
        id_str = str(table_name) + "_id"
        vector_store.add_documents(docs, ids=[doc.metadata[id_str] for doc in docs])
    except Exception as e:
        print(f"Error creating embeddings for table {table_name}: {str(e)}")


def get_docs_from_rows(table_name: str) -> list[Document]:
    """
    Fetches all rows from a table and converts them into Langchain Documents.
    Returns a list of Documents.
    """
    rows = fetch_all_rows_from_table(table_name)
    columns_types = get_all_columns_and_types(table_name)
    columns = ["id"] + [col[0] for col in columns_types]
    return create_langchain_docs_from_rows(table_name, rows, columns)

