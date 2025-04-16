from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
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

def recur_text_splitter(chunk_size=400, chunk_overlap=40, length_function=len, is_separator_regex=False):
    recur_text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=length_function,
        is_separator_regex=is_separator_regex,)
    
    return recur_text_splitter