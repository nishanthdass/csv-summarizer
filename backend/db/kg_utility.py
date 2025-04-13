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
            'section': pdf_as_llm_doc.metadata['source'],
            'documentName': pdf_as_llm_doc.metadata['pdf_file_name'],
            'toc': pdf_as_llm_doc.metadata['toc'],
            'documentParagraphNumber': pdf_as_llm_doc.metadata['block_number'],
            'sectionParagraphNumber': pdf_as_llm_doc.metadata['section_block_number'],
            'isHeader': pdf_as_llm_doc.metadata['is_header'],
            'pageNumber': pdf_as_llm_doc.metadata['page_number'],
            'hasImages': pdf_as_llm_doc.metadata['has_images'],
            'pageCount': pdf_as_llm_doc.metadata['page_count'],
            'chapterName': pdf_as_llm_doc.metadata['chapter_name'],
            'chapterNumber': pdf_as_llm_doc.metadata['chapter_number'],
            'pageId': pdf_as_llm_doc.metadata['page_id'],
            'blockId': pdf_as_llm_doc.metadata['block_id'],
            'chunkSeqIndex': pdf_as_llm_doc.metadata['chunk_seq_index'],
            'text': pdf_as_llm_doc.page_content
        }
    }

    return params


#---------------------------------------------------------------------------------------
merge_block_node_query = """
MERGE (mergedBlock:Block {blockId: $chunkParam.blockId})
    ON CREATE SET
        mergedBlock.section = $chunkParam.section,
        mergedBlock.documentName = $chunkParam.documentName,
        mergedBlock.documentParagraphNumber = $chunkParam.documentParagraphNumber,
        mergedBlock.sectionParagraphNumber = $chunkParam.sectionParagraphNumber,
        mergedBlock.isHeader = $chunkParam.isHeader,
        mergedBlock.pageNumber = $chunkParam.pageNumber,
        mergedBlock.hasImages = $chunkParam.hasImages,
        mergedBlock.pageCount = $chunkParam.pageCount,
        mergedBlock.chapterName = $chunkParam.chapterName,
        mergedBlock.chapterNumber = $chunkParam.chapterNumber,
        mergedBlock.pageId = $chunkParam.pageId,
        mergedBlock.chunkSeqIndex = $chunkParam.chunkSeqIndex,
        mergedBlock.text = $chunkParam.text
RETURN mergedBlock
"""


def create_paragraph_constraints():
    """Create constraints for paragraph nodes accross the entire document"""
    kg.query("""
        CREATE CONSTRAINT unique_block IF NOT EXISTS 
            FOR (b:Block) REQUIRE b.blockId IS UNIQUE
        """)


def add_paragraph_as_node(pdf_obj):
    """Add lines as node with metadata"""
    node_count = 0
    for line in pdf_obj:
        params = param_insert(line)
        kg.query(merge_block_node_query, 
                params=params)
        node_count += 1
    print(f"Created {node_count} nodes")



def create_document(pdf_name):
    """Create Documentt entity from Paragraph nodes"""

    kg.query(
        """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName
        MERGE (b:Document { documentName: documentName })
        RETURN b
        """, 
        params={'fileName': pdf_name})
    

def create_pages(pdf_name):
    """Create pages from Paragraph nodes"""
    
    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName, b.pageNumber AS pageNumber, b.pageId AS pageId
        MERGE (b:Page { documentName: documentName, pageNumber: pageNumber, pageId: pageId })
        RETURN b
        """

    result = kg.query(cypher, params={'fileName': pdf_name})



def create_chapters(pdf_name):
    """Create pages from Paragraph nodes"""
    
    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName, b.chapterName AS chapterName
        MERGE (b:Chapter { documentName: documentName, chapterName: chapterName })
        RETURN b
        """

    result = kg.query(cypher, params={'fileName': pdf_name})


def create_sections(pdf_name):
    """
    Create a single Section node per sectionName
    """
    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName, b.section AS sectionName
        MERGE (sec:Section {
          documentName: documentName,
          sectionName: sectionName
        })
        RETURN sec
    """
    kg.query(cypher, params={'fileName': pdf_name})



def create_sections_paragraph(pdf_name):
    """Create sections paragraph from Paragraph nodes"""
    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName, b.pageNumber AS pageNumber, b.pageId AS pageId, b.section AS sectionName, b.sectionParagraphNumber AS sectionParagraphNumber
        MERGE (b:Paragraph { documentName: documentName, pageNumber: pageNumber, pageId: pageId, sectionName: sectionName, sectionParagraphNumber: sectionParagraphNumber })
        RETURN b
        """

    result = kg.query(cypher, params={'fileName': pdf_name})

def create_chunks(pdf_name):
    """Create sections paragraph from Paragraph nodes"""
    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName, b.pageNumber AS pageNumber, b.pageId AS pageId, b.section AS sectionName, b.sectionParagraphNumber AS sectionParagraphNumber, b.chunkSeqIndex AS chunkSeqIndex, b.blockId AS blockId, b.text AS chunkText
        MERGE (b:Chunk {  blockId: blockId,  documentName: documentName, pageNumber: pageNumber, pageId: pageId, sectionName: sectionName, sectionParagraphNumber: sectionParagraphNumber, chunkSeqIndex: chunkSeqIndex, chunkText: chunkText})
        RETURN b
        """

    result = kg.query(cypher, params={'fileName': pdf_name})
    

def link_document_to_chapters(pdf_name):
    """
    Links each Chapter node to the Document it belongs to.
    """
    cypher = """
        MATCH (doc:Document {documentName: $fileName})
        MATCH (ch:Chapter {documentName: $fileName})
        MERGE (doc)-[:HAS_CHAPTER]->(ch)
    """
    kg.query(cypher, params={'fileName': pdf_name})



def link_chapters_to_pages(pdf_name):
    """
    Links each Page node to the Chapter it belongs to.
    """
    cypher = """
        MATCH (ch:Chapter {documentName: $fileName})
        MATCH (pg:Page {documentName: $fileName})
        MERGE (ch)-[:HAS_PAGE]->(pg)
    """
    kg.query(cypher, params={'fileName': pdf_name})



def link_pages_to_sections(pdf_name):
    """
    Links each Page to all Section(s) that appear on that page.
    Multiple pages can point to the same Section node.
    """
    cypher = """
        // For each page, find its blocks to see what sectionName(s) appear there.
        MATCH (pg:Page {documentName: $fileName})
        MATCH (b:Block {documentName: $fileName, pageId: pg.pageId})
        
        // Collect the distinct sectionName for that page
        WITH pg, collect(DISTINCT b.section) AS sectionNames
        
        // Unwind the list so we have (pg, sectionName) pairs
        UNWIND sectionNames AS sName
        
        // Match the single Section node for that (documentName, sName)
        MATCH (sec:Section {documentName: $fileName, sectionName: sName})
        
        // Link them
        MERGE (pg)-[:HAS_SECTION]->(sec)
    """
    kg.query(cypher, params={'fileName': pdf_name})


def link_sections_to_paragraphs(pdf_name):
    """
    Links each Paragraph node to the Section it belongs to.
    """
    cypher = """
        MATCH (sec:Section {documentName: $fileName})
        MATCH (para:Paragraph {documentName: $fileName, sectionName: sec.sectionName})
        MERGE (sec)-[:HAS_PARAGRAPH]->(para)
    """
    kg.query(cypher, params={'fileName': pdf_name})


def link_paragraphs_to_chunks(pdf_name):
    """
    Links each Chunk node to the Paragraph it belongs to.
    """
    cypher = """
        MATCH (para:Paragraph {documentName: $fileName})
        MATCH (chk:Chunk {documentName: $fileName, pageId: para.pageId, sectionName: para.sectionName, sectionParagraphNumber: para.sectionParagraphNumber})
        MERGE (para)-[:HAS_CHUNK]->(chk)
    """
    kg.query(cypher, params={'fileName': pdf_name})


def get_all_page_numbers(pdf_name):
    """Get all page numbers from documents in ascending order"""
    cypher = """
    MATCH (p:Page)
    WHERE p.documentName = $pageInfoParam
    ORDER BY p.pageNumber ASC
    RETURN p.pageNumber as pageNumber 
    """
    all_pages = kg.query(cypher, params={'pageInfoParam': pdf_name})
    return all_pages


def link_next_pages(pdf_name):
    """
    Create a :NEXT_PAGE relationship for consecutive pages based on ascending pageNumber
    within the same document.
    """
    cypher = """
        MATCH (p:Page {documentName: $fileName})
        WITH p
        ORDER BY p.pageNumber ASC
        WITH collect(p) AS pages
        CALL apoc.nodes.link(pages, 'NEXT_PAGE')
        RETURN pages
    """
    kg.query(cypher, params={'fileName': pdf_name})


def link_next_paragraphs(pdf_name):
    """
    Create a :NEXT_PARAGRAPH relationship for consecutive paragraphs 
    within each Section, ordered by ascending sectionParagraphNumber.
    """
    cypher = """
            MATCH (sec:Section {documentName: $fileName})
            MATCH (para:Paragraph {documentName: $fileName, pageId: sec.pageId, sectionName: sec.sectionName})
            WITH sec, para
            ORDER BY para.sectionParagraphNumber ASC
            WITH sec, collect(para) AS paragraphs
            CALL apoc.nodes.link(paragraphs, 'NEXT_PARAGRAPH')
            RETURN paragraphs
            """
    kg.query(cypher, params={'fileName': pdf_name})


def link_next_chunks(pdf_name):
    """
    Create a :NEXT_CHUNK relationship for consecutive chunks 
    within each Paragraph, ordered by ascending chunkSeqIndex.
    """
    cypher = """
            MATCH (para:Paragraph {documentName: $fileName})
            MATCH (chk:Chunk {
              documentName: $fileName,
              pageId: para.pageId,
              sectionName: para.sectionName,
              sectionParagraphNumber: para.sectionParagraphNumber
            })
            WITH para, chk
            ORDER BY chk.chunkSeqIndex ASC
            WITH para, collect(chk) AS chunks
            CALL apoc.nodes.link(chunks, 'NEXT_CHUNK')
            RETURN chunks
            """
    kg.query(cypher, params={'fileName': pdf_name})


def create_vector_index():
    """Create vector index for chunk nodes"""
    try:
        result = kg.query("""
            CREATE VECTOR INDEX $VECTOR_INDEX_NAME IF NOT EXISTS
            FOR (chk:Chunk) ON (chk.textEmbedding) 
            OPTIONS { 
                indexConfig: {
                    `vector.dimensions`: 512,
                    `vector.similarity_function`: 'cosine'    
                }
            }
        """, params={"VECTOR_INDEX_NAME": VECTOR_INDEX_NAME})
        
    except Exception as e:
        rprint(f"Query failed: {str(e)}")


def create_chunk_embeddings():
    """Create embeddings for Chunk nodes"""
    kg.query("""
    MATCH (chk:Chunk) WHERE chk.textEmbedding IS NULL
    WITH chk, genai.vector.encode(
      chk.chunkText, 
      "OpenAI", 
      {
        token: $openAiApiKey, 
        endpoint: $openAiEndpoint,
        model: $model,
        dimensions: 512
      }) AS vector
    CALL db.create.setNodeVectorProperty(chk, "textEmbedding", vector)
    """, 
    params={
        "openAiApiKey": openai_var.openai_api_key,
        "openAiEndpoint": openai_var.openai_endpoint,
        "model" : openai_var.openai_embedding_modal_small,
    })
    kg.refresh_schema()


    
def process_pdf_to_kg(pdf_obj, pdf_name):
    try:
        create_paragraph_constraints()
        add_paragraph_as_node(pdf_obj)
        create_document(pdf_name)
        create_chapters(pdf_name)
        create_pages(pdf_name)
        create_sections(pdf_name)
        create_sections_paragraph(pdf_name)
        create_chunks(pdf_name)
        
        link_document_to_chapters(pdf_name)
        link_chapters_to_pages(pdf_name)
        link_pages_to_sections(pdf_name)
        link_sections_to_paragraphs(pdf_name)
        link_paragraphs_to_chunks(pdf_name)
        link_next_pages(pdf_name)
        link_next_paragraphs(pdf_name)
        link_next_chunks(pdf_name)

        create_vector_index()
        create_chunk_embeddings()

    except Exception as e:
        rprint(f"Query failed: {str(e)}")