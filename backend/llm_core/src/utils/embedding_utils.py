from langchain_openai import OpenAIEmbeddings
from config import openai_var


def get_embedder(dimensions: int):
    """Get the embeddinf model"""
    embedder = OpenAIEmbeddings(
        openai_api_key=openai_var.openai_api_key,
        openai_api_base=openai_var.openai_endpoint,
        model=openai_var.openai_embedding_modal_small,
        dimensions=dimensions
    )

    return embedder