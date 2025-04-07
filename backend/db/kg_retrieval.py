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

        WITH node, closestScore,
             node.blockId     AS nClosestScoreBlockId,
             node.blockNumber AS nClosestScoreBlockNumber,
             node.chunkSeqId  AS nClosestScoreChunk,
             node.text        AS nClosestScoreText,
             node.source      AS nClosestScoreSource,
             node.pageNumber  AS nClosestScorePageNumber,
             node.isHeader    AS nClosestScoreIsHeader

        MATCH (anyPage:Page)
        WHERE anyPage.pdfFileName = '{pdf_file_name}'
        WITH node, closestScore, nClosestScorePageNumber, nClosestScoreIsHeader, nClosestScoreBlockId, nClosestScoreText, nClosestScoreBlockNumber,
             count(anyPage) AS totalPages


        MATCH (node:Block) 
        OPTIONAL MATCH (prev:Block)-[:NEXT*0..]->(node)
        WHERE prev.pdfFileName = '{pdf_file_name}'
          AND prev.pageNumber = nClosestScorePageNumber
          AND prev.blockNumber < nClosestScoreBlockNumber
          AND prev.isHeader = true
        ORDER BY prev.blockNumber DESC
        LIMIT 1
        OPTIONAL MATCH (node)-[:NEXT*0..]->(next:Block)
        WHERE next.pdfFileName = '{pdf_file_name}'
          AND next.pageNumber = nClosestScorePageNumber
          AND next.blockNumber > nClosestScoreBlockNumber
          AND next.isHeader = true
        ORDER BY next.blockNumber ASC
        LIMIT 1

        OPTIONAL MATCH p = (prev)-[:NEXT*]->(next)
        WHERE ALL(n IN nodes(p) WHERE n.pageNumber = nClosestScorePageNumber)
        WITH node, closestScore, nClosestScorePageNumber, nClosestScoreIsHeader, nClosestScoreBlockId, 
             nClosestScoreText, nClosestScoreBlockNumber, totalPages, prev, next,
             COALESCE(nodes(p)[1..-1], []) AS blocksBetween

        OPTIONAL MATCH q = (b: Block)-[:NEXT*]->(next)
        WHERE ALL(n IN nodes(q) WHERE n.pageNumber = nClosestScorePageNumber AND n.blockNumber >= 0)
        WITH node, closestScore, nClosestScorePageNumber, nClosestScoreIsHeader, nClosestScoreBlockId, 
             nClosestScoreText, nClosestScoreBlockNumber, totalPages, prev, next, blocksBetween,
             COALESCE(nodes(q)[1..-1], []) AS startToNext

        OPTIONAL MATCH r = (prev)-[:NEXT*]->(b: Block)
        WHERE ALL(n IN nodes(r) WHERE n.pageNumber = nClosestScorePageNumber AND n.blockNumber <= totalPages)
        WITH node, closestScore, nClosestScorePageNumber, nClosestScoreIsHeader, nClosestScoreBlockId, 
             nClosestScoreText, nClosestScoreBlockNumber, totalPages, prev, next, blocksBetween, startToNext,
             COALESCE(nodes(r)[1..-1], []) AS prevToEnd
             
        WITH node, closestScore, nClosestScorePageNumber, nClosestScoreIsHeader, nClosestScoreBlockId, 
             nClosestScoreText, nClosestScoreBlockNumber, totalPages, prev, next, blocksBetween, startToNext, prevToEnd,
             CASE
                 WHEN prev IS NOT NULL AND next IS NOT NULL THEN blocksBetween
                 WHEN prev IS NOT NULL AND next IS NULL THEN prevToEnd
                 ELSE startToNext
             END AS finalWindow

        
        RETURN
          // If finalWindow is an array, join the texts; adjust as needed:
          apoc.text.join([x IN finalWindow | x.text], " ") AS text,
          closestScore AS score,
          node {{
            source: node.pageNumber,
            text: node.text,
            next: next.text,
            prev: prev.text
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
