from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector
from llm_core.src.utils.embedding_utils import get_embedder
from config import openai_var, neo4j_var


VECTOR_INDEX_NAME = "pdf_lines"
VECTOR_SOURCE_PROPERTY = 'text'


def build_retrieval_query(pdf_file_name):
    """
    Builds a Cypher query to retrieve the most relevant section of a document 
    based on a similarity score.

    - Finds the closest matching chunk (`node`) and its paragraph and section.
    - Collects all sibling paragraphs and chunks from the same section.
    - Joins all chunk texts into a single section response.
    - Extracts unique page numbers from the section.

    Returns the full section text, match score, matched paragraph, 
    and metadata including section name and page numbers.
    """
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
    """Retriever window for Neo4j knowledge graph."""
    vector_store_window = Neo4jVector.from_existing_index(
        embedding=get_embedder(512),
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
