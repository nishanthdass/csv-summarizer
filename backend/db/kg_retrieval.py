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
            collect(line {{ closestScore: closestScore, lineNumber: line.lineNumber, chunkSeqId: line.chunkSeqId, text: line.text, pageNumber: line.pageNumber }}) AS additionalLines,
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

def build_column_retrieval_query(table_name):
    return f"""
        WITH node, score AS closestScore
        ORDER BY closestScore DESC LIMIT 1
        WITH node, closestScore, node.columnName AS columnName, node.rowIndex AS rowIndex, node.value AS value, "{table_name}" AS sourceTable
        MATCH (row:RowValue)
        WHERE row.tableName = "{table_name}"
        ORDER BY row.rowIndex
        WITH node, closestScore, columnName, rowIndex, value, sourceTable,
            collect(row {{ closestScore: closestScore, columnName: row.columnName, rowIndex: row.rowIndex, value: row.value }}) AS additionalLines,
            collect(row.value) AS textOnly
        RETURN
            node AS initialNode,
            apoc.text.join(textOnly, " \n ") AS text,
            closestScore AS score,
            node {{
                columnName: columnName,
                rowIndex: rowIndex,
                value: value,
                source: sourceTable,
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

    return retriever_window



def kg_column_retrieval_window(table_name):
    rprint("kg_column_retrieval_window: ", table_name)

    try:
        # rprint(f"Generated Cypher Query:\n{build_column_retrieval_query(table_name)}")
        
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
            retrieval_query= build_column_retrieval_query(table_name)
        )

        rprint("Neo4j Vector Store successfully initialized")

    except Exception as e:
        rprint(f"Error initializing vector store: {e}")
        return None

    try:
        retriever_window = vector_store_window.as_retriever()
        rprint("Retriever successfully created")
    except Exception as e:
        rprint(f"Error creating retriever: {e}")
        return None

    return retriever_window

def retreive_from_kg_by_embedddings(table_name, query_embedding):
    vector_store = Neo4jVector.from_existing_index(
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
    retrieval_query= build_column_retrieval_query(table_name)
    )

    search_results = vector_store.similarity_search_by_vector(
        query_embedding, 
        k=5  # number of results
    )