from dotenv import load_dotenv
from rich import print as rprint
from llm_core.config.load_llm_config import LoadOpenAIConfig
from config import LoadNeo4jConfig


load_dotenv()
openai_var  = LoadOpenAIConfig()
neo4j_var = LoadNeo4jConfig()
kg = neo4j_var.get_NEO4J_connection()

VECTOR_INDEX_NAME = "pdf_lines"
VECTOR_NODE_LABEL = 'Line'
VECTOR_SOURCE_PROPERTY = 'text'
VECTOR_EMBEDDING_PROPERTY = 'textEmbedding'

def param_insert(pdf_as_llm_doc):
    '''
    Format params for Neo4j query
    '''
    params = {
        'chunkParam': {
            'source': pdf_as_llm_doc.metadata['source'],
            'pdfFileName': pdf_as_llm_doc.metadata['pdf_file_name'],
            'toc': pdf_as_llm_doc.metadata['toc'],
            'blockNumber': pdf_as_llm_doc.metadata['block_number'],
            'isHeader': pdf_as_llm_doc.metadata['is_header'],
            'pageNumber': pdf_as_llm_doc.metadata['page_number'],
            'hasImages': pdf_as_llm_doc.metadata['has_images'],
            'pageCount': pdf_as_llm_doc.metadata['page_count'],
            'chapterName': pdf_as_llm_doc.metadata['chapter_name'],
            'chapterNumber': pdf_as_llm_doc.metadata['chapter_number'],
            'pageId': pdf_as_llm_doc.metadata['page_id'],
            'blockId': pdf_as_llm_doc.metadata['block_id'],
            'chunkSeqId': pdf_as_llm_doc.metadata['chunk_seq_id'],
            'text': pdf_as_llm_doc.page_content
        }
    }

    return params


#---------------------------------------------------------------------------------------
merge_block_node_query = """
MERGE (mergedBlock:Block {blockId: $chunkParam.blockId})
    ON CREATE SET
        mergedBlock.source = $chunkParam.source,
        mergedBlock.pdfFileName = $chunkParam.pdfFileName,
        mergedBlock.blockNumber = $chunkParam.blockNumber,
        mergedBlock.isHeader = $chunkParam.isHeader,
        mergedBlock.pageNumber = $chunkParam.pageNumber,
        mergedBlock.hasImages = $chunkParam.hasImages,
        mergedBlock.pageCount = $chunkParam.pageCount,
        mergedBlock.chapterName = $chunkParam.chapterName,
        mergedBlock.chapterNumber = $chunkParam.chapterNumber,
        mergedBlock.pageId = $chunkParam.pageId,
        mergedBlock.chunkSeqId = $chunkParam.chunkSeqId,
        mergedBlock.text = $chunkParam.text
RETURN mergedBlock
"""


def create_block_constraints():
    """Create constraints for paragraph nodes"""
    kg.query("""
        CREATE CONSTRAINT unique_paragraph IF NOT EXISTS 
            FOR (b:Block) REQUIRE b.blockId IS UNIQUE
        """)


def add_block_as_node(pdf_obj):
    """Add lines as node with metadata"""
    node_count = 0
    for line in pdf_obj:
        params = param_insert(line)
        kg.query(merge_block_node_query, 
                params=params)
        node_count += 1
    print(f"Created {node_count} nodes")



def create_pdfname_from_block_nodes(pdf_name):
    """Create PDF entity from line nodes"""

    kg.query(
        """
        MATCH (b:Block)
        WHERE b.pdfFileName = $fileName
        WITH DISTINCT b.pdfFileName AS pdfFileName
        MERGE (b:PdfName { pdfFileName: pdfFileName })
        RETURN b
        """, 
        params={'fileName': pdf_name})
    

def create_pages_from_block_nodes(pdf_name):
    """Create pages from line nodes"""
    
    cypher = """
        MATCH (b:Block)
        WHERE b.pdfFileName = $fileName
        WITH DISTINCT b.pdfFileName AS pdfFileName, b.pageNumber AS pageNumber, b.pageId AS pageId
        MERGE (p:Page { pdfFileName: pdfFileName, pageNumber: pageNumber, pageId: pageId })
        RETURN p
        """

    result = kg.query(cypher, params={'fileName': pdf_name})



def create_block_vector_index():
    """Create vector index for line nodes"""
    try:
        result = kg.query("""
            CREATE VECTOR INDEX $VECTOR_INDEX_NAME IF NOT EXISTS
            FOR (b:Block) ON (b.textEmbedding) 
            OPTIONS { 
                indexConfig: {
                    `vector.dimensions`: 512,
                    `vector.similarity_function`: 'cosine'    
                }
            }
        """, params={"VECTOR_INDEX_NAME": VECTOR_INDEX_NAME})
        
    except Exception as e:
        rprint(f"Query failed: {str(e)}")


def create_block_embeddings():
    """Create embeddings for line nodes"""
    kg.query("""
    MATCH (b:Block) WHERE b.textEmbedding IS NULL
    WITH b, genai.vector.encode(
      b.text, 
      "OpenAI", 
      {
        token: $openAiApiKey, 
        endpoint: $openAiEndpoint,
        model: $model,
        dimensions: 512
      }) AS vector
    CALL db.create.setNodeVectorProperty(b, "textEmbedding", vector)
    """, 
    params={
        "openAiApiKey": openai_var.openai_api_key,
        "openAiEndpoint": openai_var.openai_endpoint,
        "model" : openai_var.openai_embedding_modal_small,
    })
    kg.refresh_schema()



def get_all_page_numbers(pdf_name):
    """Get all page numbers from documents in ascending order"""
    cypher = """
    MATCH (p:Page)
    WHERE p.pdfFileName = $pageInfoParam
    ORDER BY p.pageNumber ASC
    RETURN p.pageNumber as pageNumber 
    """
    all_pages = kg.query(cypher, params={'pageInfoParam': pdf_name})
    return all_pages


def match_block_sequence_nodes(page_number, pdf_name):
    """Match block nodes to block nodes with the same page number and order by block number and chunk sequence id"""
    
    cypher = """
                MATCH (from_same_page:Block)
                    WHERE from_same_page.pageNumber = $blockIdParam and from_same_page.pdfFileName = $pageInfoParam
                WITH from_same_page
                    ORDER BY from_same_page.blockNumber ASC, from_same_page.chunkSeqId ASC
                WITH collect(from_same_page) as section_chunk_list
                    CALL apoc.nodes.link(
                        section_chunk_list, 
                        "NEXT", 
                        {avoidDuplicates: true}
                    ) 
                RETURN size(section_chunk_list)
            """
    
    kg.query(cypher, params={'blockIdParam': page_number, 'pageInfoParam': pdf_name})


def connect_block_to_page(pdf_name):

    cypher = """
                MATCH (b:Block), (p:Page)
                    WHERE b.pageId = p.pageId AND b.pdfFileName = $pageInfoParam
                MERGE (b)-[newRelationship:PART_OF]->(p)
                RETURN count(newRelationship)
            """

    result = kg.query(cypher, params={'pageInfoParam': pdf_name})


    
def process_pdf_to_kg(pdf_obj, pdf_name):
    try:
        create_block_constraints()
        add_block_as_node(pdf_obj)
        create_pages_from_block_nodes(pdf_name)
        create_pdfname_from_block_nodes(pdf_name)
        page_numbers = get_all_page_numbers(pdf_name)
        for page_info in page_numbers:
            match_block_sequence_nodes(page_info['pageNumber'], pdf_name)

        connect_block_to_page(pdf_name)
        create_block_vector_index()
        create_block_embeddings()

    except Exception as e:
        rprint(f"Query failed: {str(e)}")