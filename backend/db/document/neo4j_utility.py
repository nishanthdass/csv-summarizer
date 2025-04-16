from dotenv import load_dotenv
from rich import print as rprint
from config import neo4j_var, openai_var


load_dotenv()
kg = neo4j_var.get_neo4j_connection()


VECTOR_INDEX_NAME = "pdf_lines"
VECTOR_SOURCE_PROPERTY = 'text'


def param_insert(pdf_as_llm_doc):
    '''
    Format params for Neo4j chunk insert
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


def create_block_constraints():
    """Create constraints for Block nodes"""
    kg.query("""
        CREATE CONSTRAINT unique_block IF NOT EXISTS 
            FOR (b:Block) REQUIRE b.blockId IS UNIQUE
        """)


def add_block_as_node(pdf_obj):
    """Add each block as node with metadata"""
    node_count = 0
    for line in pdf_obj:
        params = param_insert(line)
        kg.query(merge_block_node_query, 
                params=params)
        node_count += 1


def create_document(pdf_name):
    """Create Document entity from Block nodes"""

    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName
        MERGE (b:Document { documentName: documentName })
        RETURN b
        """

    kg.query(cypher, params={'fileName': pdf_name})
    

def create_pages(pdf_name):
    """Create pages from Block nodes"""
    
    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName, b.pageNumber AS pageNumber, b.pageId AS pageId
        MERGE (b:Page { documentName: documentName, pageNumber: pageNumber, pageId: pageId })
        RETURN b
        """

    kg.query(cypher, params={'fileName': pdf_name})



def create_chapters(pdf_name):
    """Create pages from Block nodes"""
    
    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName, b.chapterName AS chapterName
        MERGE (b:Chapter { documentName: documentName, chapterName: chapterName })
        RETURN b
        """

    kg.query(cypher, params={'fileName': pdf_name})


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
    """Create sections paragraph from Block nodes"""

    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName, b.pageNumber AS pageNumber, b.pageId AS pageId, b.section AS sectionName, b.sectionParagraphNumber AS sectionParagraphNumber
        MERGE (b:Paragraph { documentName: documentName, pageNumber: pageNumber, pageId: pageId, sectionName: sectionName, sectionParagraphNumber: sectionParagraphNumber })
        RETURN b
        """

    kg.query(cypher, params={'fileName': pdf_name})


def create_chunks(pdf_name):
    """Create chunks from Block nodes"""

    cypher = """
        MATCH (b:Block)
        WHERE b.documentName = $fileName
        WITH DISTINCT b.documentName AS documentName, b.pageNumber AS pageNumber, b.pageId AS pageId, b.section AS sectionName, b.sectionParagraphNumber AS sectionParagraphNumber, b.chunkSeqIndex AS chunkSeqIndex, b.blockId AS blockId, b.text AS chunkText
        MERGE (b:Chunk {  blockId: blockId,  documentName: documentName, pageNumber: pageNumber, pageId: pageId, sectionName: sectionName, sectionParagraphNumber: sectionParagraphNumber, chunkSeqIndex: chunkSeqIndex, chunkText: chunkText})
        RETURN b
        """

    kg.query(cypher, params={'fileName': pdf_name})
    

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
    Links each Page to all sections that appear on that page.
    Multiple pages can point to the same Section node.
    """
    cypher = """
        MATCH (pg:Page {documentName: $fileName})
        MATCH (b:Block {documentName: $fileName, pageId: pg.pageId})
        WITH pg, collect(DISTINCT b.section) AS sectionNames
        UNWIND sectionNames AS sName
        MATCH (sec:Section {documentName: $fileName, sectionName: sName})
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
        query = """
                CREATE VECTOR INDEX $VECTOR_INDEX_NAME IF NOT EXISTS
                FOR (chk:Chunk) ON (chk.textEmbedding) 
                OPTIONS { 
                    indexConfig: {
                        `vector.dimensions`: 512,
                        `vector.similarity_function`: 'cosine'    
                    }
                }
                """
        kg.query(query, params={"VECTOR_INDEX_NAME": VECTOR_INDEX_NAME})
        
    except Exception as e:
        rprint(f"Query failed: {str(e)}")


def create_chunk_embeddings():
    """Create embeddings for Chunk nodes"""
    cypher = """
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
            """
    kg.query(cypher, 
        params={
            "openAiApiKey": openai_var.openai_api_key,
            "openAiEndpoint": openai_var.openai_endpoint,
            "model" : openai_var.openai_embedding_modal_small,
        })
    kg.refresh_schema()


    
def process_pdf_to_kg(pdf_obj, pdf_name):
    try:
        # Insert blocks that make up the document
        # Blocks contain metadata to create entities
        create_block_constraints()
        add_block_as_node(pdf_obj)
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