import textwrap
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector
from rich import print as rprint
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_openai import ChatOpenAI
from qa_with_postgres.load_config import LoadOpenAIConfig, LoadNeo4jConfig
from langchain_core.prompts import PromptTemplate

openai_var  = LoadOpenAIConfig()
neo4j_var = LoadNeo4jConfig()


VECTOR_INDEX_NAME = "pdf_lines"
VECTOR_NODE_LABEL = 'Line'
VECTOR_SOURCE_PROPERTY = 'text'
VECTOR_EMBEDDING_PROPERTY = 'textEmbedding'


def build_retrieval_query(pdf_file_name):
    return f"""
        WITH node, score AS closestScore
        ORDER BY closestScore DESC LIMIT 1
        WITH node, closestScore, node.lineNumber AS startingLine, node.source AS startingSource, node.text AS nodeText
        MATCH (line:Line)
        WHERE line.source = startingSource AND line.pdfFileName = "{pdf_file_name}"
        ORDER BY line.lineNumber, line.chunkSeqId ASC
        WITH node, closestScore, nodeText, startingLine, startingSource,
            collect(line {{ lineNumber: line.lineNumber, chunkSeqId: line.chunkSeqId, text: line.text }}) AS additionalLines,
            collect(line.text) AS textOnly
        RETURN
            apoc.text.join(textOnly, " \n ") AS text,
            closestScore AS score,
            node {{
                lineNumber: startingLine,
                source: startingSource,
                additionalLines: additionalLines
            }} AS metadata
    """


def kg_retrieval_window(pdf_name):
    vector_store_window = Neo4jVector.from_existing_index(
        embedding=OpenAIEmbeddings(
            openai_api_key=openai_var.openai_api_key,
            openai_api_base=openai_var.openai_endpoint,
            model=openai_var.openai_embedding_model
        ),
        url=neo4j_var.neo4j_uri,
        username=neo4j_var.neo4j_user,
        password=neo4j_var.neo4j_password,
        database=neo4j_var.neo4j_db,
        index_name=VECTOR_INDEX_NAME,
        text_node_property=VECTOR_SOURCE_PROPERTY,
        retrieval_query= build_retrieval_query(pdf_name)
    )

    retriever_window = vector_store_window.as_retriever(
    )

    rprint("retriever_window: ", retriever_window)

    return retriever_window

