from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector
from rich import print as rprint
from llm_core.config.load_llm_config import LoadOpenAIConfig
from config import LoadNeo4jConfig

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
        WITH node, closestScore, node.lineNumber AS startingLine, node.source AS startingSource, node.text AS nodeText, node.pageNumber AS nodePage
        MATCH (line:Line)
        WHERE line.source = startingSource AND line.pdfFileName = "{pdf_file_name}" AND line.pageNumber = nodePage
        ORDER BY line.lineNumber, line.chunkSeqId ASC
        WITH node, closestScore, nodeText, startingLine, startingSource, nodePage,
            collect(line {{ lineNumber: line.lineNumber, chunkSeqId: line.chunkSeqId, text: line.text, pageNumber: line.pageNumber }}) AS additionalLines,
            collect(line.text) AS textOnly
        RETURN
            apoc.text.join(textOnly, " \n ") AS text,
            closestScore AS score,
            node {{
                lineNumber: startingLine,
                pageNumber: nodePage,
                source: startingSource,
                additionalLines: additionalLines
            }} AS metadata
    """

# def build_column_retrieval_query(table_name):
#     return f"""
#         WITH node, score AS closestScore
#         ORDER BY closestScore DESC
#         LIMIT 5
#         MATCH (rowValue:RowValue)-[r:VALUE_OF]->(node:Column)
#         WHERE node.tableName = "{table_name}"

#         WITH node, closestScore, node.columnName AS columnName,
#              collect({{ 
#                 rowValueId: rowValue.rowValueId, 
#                 value: rowValue.value 
#              }}) AS rowValues

#         RETURN 
#             columnName, 
#             rowValues AS values,
#             closestScore AS score
#     """



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

    return retriever_window

# def kg_column_retrieval_window(pdf_name):
#     vector_store_window = Neo4jVector.from_existing_index(
#         embedding=OpenAIEmbeddings(
#             openai_api_key=openai_var.openai_api_key,
#             openai_api_base=openai_var.openai_endpoint,
#             model=openai_var.openai_embedding_model
#         ),
#         url=neo4j_var.neo4j_uri,
#         username=neo4j_var.neo4j_user,
#         password=neo4j_var.neo4j_password,
#         database=neo4j_var.neo4j_db,
#         index_name=VECTOR_INDEX_NAME,
#         text_node_property=VECTOR_SOURCE_PROPERTY,
#         retrieval_query= build_column_retrieval_query(pdf_name)
#     )

#     retriever_window = vector_store_window.as_retriever(
#     )

#     return retriever_window

