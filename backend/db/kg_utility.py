from dotenv import load_dotenv
from utils.pdf_processing_funct import param_insert
from utils.table_processing_funct import param_insert_csv, param_insert_csv_row_values
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

#---------------------------------------------------------------------------------------

merge_line_node_query = """
MERGE (mergedLine:Line {lineId: $chunkParam.lineId})
    ON CREATE SET
        mergedLine.source = $chunkParam.source,
        mergedLine.pdfFileName = $chunkParam.pdfFileName,
        mergedLine.lineNumber = $chunkParam.lineNumber,
        mergedLine.pageNumber = $chunkParam.pageNumber,
        mergedLine.hasImages = $chunkParam.hasImages,
        mergedLine.altTitle = $chunkParam.altTitle,
        mergedLine.pageCount = $chunkParam.pageCount,
        mergedLine.chapterName = $chunkParam.chapterName,
        mergedLine.chapterNumber = $chunkParam.chapterNumber,
        mergedLine.pageId = $chunkParam.pageId,
        mergedLine.chunkSeqId = $chunkParam.chunkSeqId,
        mergedLine.text = $chunkParam.text
RETURN mergedLine
"""


merge_column_node_query = """
MERGE (mergedColumn:Column {columnId: $chunkParam.columnId})
    ON CREATE SET
        mergedColumn.tableName = $chunkParam.tableName,
        mergedColumn.columnName = $chunkParam.columnName,
        mergedColumn.columnType = $chunkParam.columnType
RETURN mergedColumn
"""


merge_row_index_node_query = """
MERGE (mergedRowValue:RowIndex {rowValueId: $chunkParam.rowValueId})
    ON CREATE SET
        mergedRowValue.rowIndex = $chunkParam.rowIndex
RETURN mergedRowValue
"""


merge_row_value_node_query = """
MERGE (mergedRowValue:RowValue {rowValueId: $chunkParam.rowValueId})
    ON CREATE SET
        mergedRowValue.tableName = $chunkParam.tableName,
        mergedRowValue.columnName = $chunkParam.columnName,
        mergedRowValue.value = $chunkParam.value,
        mergedRowValue.rowIndex = $chunkParam.rowIndex
RETURN mergedRowValue
"""


def create_line_constraints():
    """Create constraints for line nodes"""
    kg.query("""
        CREATE CONSTRAINT unique_line IF NOT EXISTS 
            FOR (l:Line) REQUIRE l.lineId IS UNIQUE
        """)


def add_line_as_node(pdf_obj):
    """Add lines as node with metadata"""
    node_count = 0
    for line in pdf_obj:
        params = param_insert(line)
        kg.query(merge_line_node_query, 
                params=params)
        node_count += 1
    print(f"Created {node_count} nodes")


def create_line_vector_index():
    """Create vector index for line nodes"""
    try:
        result = kg.query("""
            CREATE VECTOR INDEX $VECTOR_INDEX_NAME IF NOT EXISTS
            FOR (l:Line) ON (l.textEmbedding) 
            OPTIONS { 
                indexConfig: {
                    `vector.dimensions`: 512,
                    `vector.similarity_function`: 'cosine'    
                }
            }
        """, params={"VECTOR_INDEX_NAME": VECTOR_INDEX_NAME})
        rprint(f"Query successful: {result}")
    except Exception as e:
        rprint(f"Query failed: {str(e)}")


def create_line_embeddings():
    """Create embeddings for line nodes"""
    kg.query("""
    MATCH (line:Line) WHERE line.textEmbedding IS NULL
    WITH line, genai.vector.encode(
      line.text, 
      "OpenAI", 
      {
        token: $openAiApiKey, 
        endpoint: $openAiEndpoint,
        model: $model,
        dimensions: 512
      }) AS vector
    CALL db.create.setNodeVectorProperty(line, "textEmbedding", vector)
    """, 
    params={
        "openAiApiKey": openai_var.openai_api_key,
        "openAiEndpoint": openai_var.openai_endpoint,
        "model" : openai_var.openai_embedding_modal_small,
    })
    kg.refresh_schema()


def return_any_line(file_name_minus_extension):
    """Return any line for a given page"""
    cypher = """
    MATCH (anyLine:Line)
    WHERE anyLine.pdfFileName = $pageInfoParam
    WITH anyLine LIMIT 1
    RETURN anyLine { .lineId, .pageId, .source, .pdfFileName, .lineNumber, .pageNumber, .hasImages, .altTitle, .pageCount, .chapterName, .chapterNumber, .chunkSeqId } as pageInfo
    """
    any_chunk = kg.query(cypher, params={'pageInfoParam': file_name_minus_extension})
    return any_chunk


def create_pages_from_line_nodes(file_name_minus_extension):
    """Create pages from line nodes"""
    cypher = """
        MATCH (l:Line)
        WHERE l.pdfFileName = $fileName
        WITH DISTINCT l.pdfFileName AS pdfFileName, l.pageNumber AS pageNumber, l.pageId AS pageId
        MERGE (p:Page { pdfFileName: pdfFileName, pageNumber: pageNumber, pageId: pageId })
        RETURN p
        """
    rprint("Begin create_pages_from_line_nodes")
    result =kg.query(cypher, params={'fileName': file_name_minus_extension})
    rprint("End create_pages_from_line_nodes")
    rprint(result)



def create_pdfname_from_line_nodes(file_name_minus_extension):
    """Create Book entity from line nodes"""
    kg.query(
        """
        MATCH (l:Line)
        WHERE l.pdfFileName = $fileName
        WITH DISTINCT l.pdfFileName AS pdfFileName
        MERGE (b:Bookname { pdfFileName: pdfFileName })
        RETURN b
        """, 
        params={'fileName': file_name_minus_extension}
    )


def get_all_page_numbers(file_name_minus_extension):
    """Get all page numbers from documents in ascending order"""
    cypher = """
    MATCH (p:Page)
    WHERE p.pdfFileName = $pageInfoParam
    ORDER BY p.pageNumber ASC
    RETURN p.pageNumber as pageNumber 
    """
    all_pages = kg.query(cypher, params={'pageInfoParam': file_name_minus_extension})
    return all_pages


def match_line_sequence_nodes(page_number, file_name_minus_extension):
    """Match line nodes to page nodes and order by line number and chunk sequence id"""
    cypher = """
                MATCH (from_same_page:Line)
                    WHERE from_same_page.pageNumber = $lineIdParam and from_same_page.pdfFileName = $pageInfoParam
                WITH from_same_page
                    ORDER BY from_same_page.lineNumber ASC, from_same_page.chunkSeqId ASC
                WITH collect(from_same_page) as section_chunk_list
                    CALL apoc.nodes.link(
                        section_chunk_list, 
                        "NEXT", 
                        {avoidDuplicates: true}
                    ) 
                RETURN size(section_chunk_list)
            """
    
    kg.query(cypher, params={'lineIdParam': page_number, 'pageInfoParam': file_name_minus_extension})


def connect_line_to_page(file_name_minus_extension):
    cypher = """
                MATCH (l:Line), (p:Page)
                    WHERE l.pageId = p.pageId AND l.pdfFileName = $pageInfoParam
                MERGE (l)-[newRelationship:PART_OF]->(p)
                RETURN count(newRelationship)
            """

    result = kg.query(cypher, params={'pageInfoParam': file_name_minus_extension})
    rprint(result)


def create_line_section_relationships(file_name_minus_extension):
    cypher = """
                MATCH (first:Line), (p:Page)
                WHERE first.pageId = p.pageId AND first.pdfFileName = $pageInfoParam AND first.chunkSeqId = 0
                WITH first, p
                    MERGE (p)-[r:HAS_LINE_HEAD {pageNumber: first.pageNumber}]->(first)
                RETURN count(r)
            """

    kg.query(cypher, params={'pageInfoParam': file_name_minus_extension})

    
def process_pdf_to_kg(pdf_obj, file_name_minus_extension):
    try:
        rprint("Begin processing")
        rprint(f"Processing {file_name_minus_extension}")
        rprint("Creating line nodes...")
        create_line_constraints()
        rprint("Adding line nodes...")
        add_line_as_node(pdf_obj)
        rprint("Creating line vector index...")
        create_line_vector_index()
        rprint("Creating line embeddings...")
        create_line_embeddings()
        rprint("Creating page nodes...")
        create_pages_from_line_nodes(file_name_minus_extension)
        rprint("Creating pdfname node...")
        create_pdfname_from_line_nodes(file_name_minus_extension)
        rprint("Getting all lines...")
        all_lines = get_all_page_numbers(file_name_minus_extension)
        rprint("Matching line sequence nodes...")
        for line in all_lines:
            match_line_sequence_nodes(line['pageNumber'], file_name_minus_extension)
        rprint("Connecting line nodes to page nodes...")
        connect_line_to_page(file_name_minus_extension)
        create_line_section_relationships(file_name_minus_extension)
    except Exception as e:
        rprint(f"Query failed: {str(e)}")