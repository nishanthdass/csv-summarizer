from dotenv import load_dotenv
from utils.pdf_processing_funct import param_insert
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

def return_any_chunk():
    cypher = """
    MATCH (anyChunk:Chunk) 
    WITH anyChunk LIMIT 1
    RETURN anyChunk { .chunkId, .source, .pdfFileName, .lineNumber, .pageNumber, .hasImages, .altTitle, .pageCount, .chapterName, .chapterNumber, .chunkSeqId } as pageInfo
    """
    any_chunk = kg.query(cypher)
    return any_chunk


def return_all_chunks():
    cypher = """
    MATCH (anyChunk:Chunk) 
    RETURN anyChunk { .chunkId, .source, .lineNumber, .pageNumber, .hasImages, .altTitle, .pageCount, .chapterName, .chapterNumber, .chunkSeqId } as pageInfo
    """
    all_chunks = kg.query(cypher)
    return all_chunks



def make_page_identifier_nodes(page_info):

    rprint(page_info)
    cypher = """
    MERGE (p:Page {chunkId: $pageInfoParam.chunkId })
      ON CREATE 
        SET p.pageNumber = $pageInfoParam.pageNumber
        SET p.source = $pageInfoParam.source
        SET p.chunkSeqId = $pageInfoParam.chunkSeqId
        SET p.lineNumber = $pageInfoParam.lineNumber
    """
    kg.query(cypher, params={'pageInfoParam': page_info})


def make_pages_identifier_nodes(page_info):

    rprint(page_info)
    cypher = """
    MERGE (p:Page {lineId: $pageInfoParam.lineId })
      ON CREATE 
        SET p.pageNumber = $pageInfoParam.pageNumber
        SET p.pdfFileName = $pageInfoParam.pdfFileName
    """
    kg.query(cypher, params={'pageInfoParam': page_info})

def count_page_nodes():
    page_count = kg.query("MATCH (p:Page) RETURN count(p) as pageCount")
    return page_count

def view_labels():
    labels = kg.query("MATCH (n) RETURN distinct labels(n)")
    return labels


def connect_chunk_to_parent():
    cypher = """
                MATCH (c:Chunk), (p:Page)
                    WHERE c.chunkId = p.chunkId
                MERGE (c)-[newRelationship:PART_OF]->(p)
                RETURN count(newRelationship)
            """

    kg.query(cypher)

def connect_line_to_parent():
    cypher = """
                MATCH (l:Line), (p:Page)
                    WHERE l.lineId = p.chunkId
                MERGE (l)-[newRelationship:PART_OF]->(p)
                RETURN count(newRelationship)
            """

    kg.query(cypher)

def create_section_relationships():
    cypher = """
                MATCH (first:Chunk), (p:Page)
                WHERE first.chunkId = p.chunkId
                    AND first.chunkSeqId = 0
                WITH first, p
                    MERGE (p)-[r:SECTION {pageNumber: first.pageNumber}]->(first)
                RETURN count(r)
            """

    kg.query(cypher)




def get_first_chunk_from_section(page_info):
    cypher = """
                MATCH (p:Page)-[r:SECTION]->(first:Chunk)
                    WHERE p.chunkId = $pageIdParam
                        AND r.pageNumber = $pageNumParam
                RETURN first.chunkId as chunkId, first.text as text
            """

    first_chunk_info = kg.query(cypher, params={
        'pageIdParam': page_info['chunkId'], 
        'pageNumParam': page_info['pageNumber']
    })[0]

    return first_chunk_info


def get_second_chunk_from_section(first_chunk_info):
    cypher = """
    MATCH (first:Chunk)-[:NEXT]->(nextChunk:Chunk)
        WHERE first.chunkId = $chunkIdParam
    RETURN nextChunk.chunkId as chunkId, nextChunk.text as text
    """

    next_chunk_info = kg.query(cypher, params={
        'chunkIdParam': first_chunk_info['chunkId']
    })[0]

    return next_chunk_info

def return_three_chunks_from_section(next_chunk_info):
    rprint(next_chunk_info['chunkId'])
    cypher = """
                MATCH (c1:Chunk)-[:NEXT]->(c2:Chunk)-[:NEXT]->(c3:Chunk) 
                    WHERE c2.chunkId = $chunkIdParam
                RETURN c1.chunkId, c2.chunkId, c3.chunkId, c1.text, c2.text, c3.text, c1.lineNumber, c2.lineNumber, c3.lineNumber
            """

    three_chunks = kg.query(cypher,
            params={'chunkIdParam': 'single-page-ml-1-11-chunk0000'})

    return three_chunks

def return_longest_window(first_chunk_info):
    cypher = """
                MATCH window=
                    (:Chunk)-[:NEXT*0..1]->(c:Chunk)-[:NEXT*0..1]->(:Chunk)
                    WHERE c.chunkId = $chunkIdParam
                WITH window as longestChunkWindow 
                    ORDER BY length(window) DESC LIMIT 1
                RETURN length(longestChunkWindow)
            """

    length = kg.query(cypher,
            params={'chunkIdParam': first_chunk_info['chunkId']})

    return length



def refresh_schema():
    kg.refresh_schema()
    print(kg.schema)


# def create_constraints():
#     kg.query("""
#         CREATE CONSTRAINT unique_chunk IF NOT EXISTS 
#             FOR (c:Chunk) REQUIRE c.chunkId IS UNIQUE
#         """)
    


# def add_chunk_as_node(pdf_obj):
#     node_count = 0
#     for chunk in pdf_obj:
#         params = param_insert(chunk)
#         kg.query(merge_chunk_node_query, 
#                 params=params)
#         node_count += 1
#     print(f"Created {node_count} nodes")


def view_nodes_constraints_indexes():
    show_nodes = kg.query("""MATCH (n) RETURN n""")

    for node in show_nodes:
        rprint(node['n']['source'])
        rprint(node["n"]['text'])
        # if "STEP 1" in node["n"]["text"]:
        #     rprint(node["n"])
    # show_index = kg.query("""SHOW INDEXES""")
    # rprint("Indexes: \n", show_index)

    # show_constraints = kg.query("""SHOW CONSTRAINTS""")
    # rprint("Constraints: \n", show_constraints)

    # show_vector_indexes = kg.query("""SHOW VECTOR INDEXES""")
    # rprint("Vector Indexes: \n", show_vector_indexes)


def remove_nodes():
    delete_nodes = kg.query("""MATCH (n) DETACH DELETE n""")
    rprint(delete_nodes)


# def create_vector_index():
#     rprint("Creating vector index: ", VECTOR_INDEX_NAME)
#     try:
#         result = kg.query("""
#             CREATE VECTOR INDEX $VECTOR_INDEX_NAME IF NOT EXISTS
#             FOR (c:Chunk) ON (c.textEmbedding) 
#             OPTIONS { 
#                 indexConfig: {
#                     `vector.dimensions`: 3072,
#                     `vector.similarity_function`: 'cosine'    
#                 }
#             }
#         """, params={"VECTOR_INDEX_NAME": VECTOR_INDEX_NAME})
#         rprint(f"Query successful: {result}")
#     except Exception as e:
#         rprint(f"Query failed: {str(e)}")



# def create_embeddings():
#     rprint("Creating embeddings with specified model")
#     kg.query("""
#     MATCH (chunk:Chunk) WHERE chunk.textEmbedding IS NULL
#     WITH chunk, genai.vector.encode(
#       chunk.text, 
#       "OpenAI", 
#       {
#         token: $openAiApiKey, 
#         endpoint: $openAiEndpoint,
#         model: $model,
#         dimensions: 3072
#       }) AS vector
#     CALL db.create.setNodeVectorProperty(chunk, "textEmbedding", vector)
#     """, 
#     params={
#         "openAiApiKey": openai_var.openai_api_key,
#         "openAiEndpoint": openai_var.openai_endpoint,
#         "model" : openai_var.openai_embedding_model,
#     })
#     kg.refresh_schema()
#     print(kg.schema)


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
                    `vector.dimensions`: 3072,
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
        dimensions: 3072
      }) AS vector
    CALL db.create.setNodeVectorProperty(line, "textEmbedding", vector)
    """, 
    params={
        "openAiApiKey": openai_var.openai_api_key,
        "openAiEndpoint": openai_var.openai_endpoint,
        "model" : openai_var.openai_embedding_model,
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


def return_all_lines(file_name_minus_extension):
    """Return all lines from document"""
    cypher = """
    MATCH (anyLine:Line)
    WHERE anyLine.pdfFileName = $pageInfoParam
    RETURN anyLine { .lineId, .pageId, .source, .pdfFileName, .lineNumber, .pageNumber, .hasImages, .altTitle, .pageCount, .chapterName, .chapterNumber, .chunkSeqId } as pageInfo
    """
    all_lines = kg.query(cypher, params={'pageInfoParam': file_name_minus_extension})
    return all_lines


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


def match_line_sequence_nodes(page_number):
    """Match line nodes to page nodes and order by line number and chunk sequence id"""
    cypher = """
                MATCH (from_same_page:Line)
                    WHERE from_same_page.pageNumber = $lineIdParam
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
    
    kg.query(cypher, params={'lineIdParam': page_number})


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
                WHERE first.pageId = p.pageId
                    AND first.chunkSeqId = 0
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
            match_line_sequence_nodes(line['pageNumber'])
        rprint("Connecting line nodes to page nodes...")
        connect_line_to_page(file_name_minus_extension)
        create_line_section_relationships(file_name_minus_extension)
    except Exception as e:
        rprint(f"Query failed: {str(e)}")


# file_name = "Mathematics-Methods-for-Early-Childhood-1620843562_Delete"
# connect_line_to_page(file_name)