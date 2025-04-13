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
        ORDER BY closestScore DESC
        LIMIT 1

        // Get section name
        MATCH (node)<-[:HAS_CHUNK]-(closestParagraph:Paragraph)<-[:HAS_PARAGRAPH]-(sec:Section)
        // Get all paragrahs and chunks from section
        MATCH (sec)-[:HAS_PARAGRAPH]->(siblingParagraph:Paragraph)-[:HAS_CHUNK]->(siblingChunk:Chunk)

        WITH
            node,
            closestParagraph,
            closestScore,
            sec.sectionName AS sectionName,
            collect(DISTINCT siblingParagraph) AS allParagraphs,
            collect(DISTINCT siblingChunk.chunkText) AS fullSectionChunks

        // create a pageNumbers list from each paragraph’s pageNumber
        WITH
            node,
            closestParagraph,
            closestScore,
            sectionName,
            // extract pageNumber from each paragraph in allParagraphs
            apoc.convert.toSet([p in allParagraphs WHERE p.pageNumber IS NOT NULL | p.pageNumber]) AS pageNumbers,
            // build section response from all chunk texts
            apoc.text.join(fullSectionChunks, ' ') AS sectionResponse

        RETURN
          sectionResponse AS text,
          closestScore   AS score,
          closestParagraph AS matchedParagraph,
          node {{
            closestText: node.text,
            sectionName: sectionName,
            pageNumbers: pageNumbers,
            source: sectionName
          }} AS metadata
    """



def kg_retrieval_window(file_name):
    """retriever for the knowledge graph"""
    vector_store_window = Neo4jVector.from_existing_index(
        embedding=OpenAIEmbeddings(
            openai_api_key=openai_var.openai_api_key,
            openai_api_base=openai_var.openai_endpoint,
            model=openai_var.openai_embedding_modal_small,
            dimensions=512
        ),
        url=neo4j_var.neo4j_uri,
        username=neo4j_var.neo4j_user,
        password=neo4j_var.neo4j_password,
        database=neo4j_var.neo4j_db,
        index_name=VECTOR_INDEX_NAME,
        text_node_property=VECTOR_SOURCE_PROPERTY,
        retrieval_query= build_retrieval_query(file_name)
    )
    retriever_window = vector_store_window.as_retriever(
    )
    return retriever_window
