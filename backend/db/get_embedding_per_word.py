import sys
import re
from rich import print as rprint
from langchain_openai import OpenAIEmbeddings
import ast
import os
import psycopg2
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from neo4j import GraphDatabase
from config import LoadNeo4jConfig, LoadPostgresConfig
from llm_core.config.load_llm_config import LoadOpenAIConfig


db = LoadPostgresConfig()
openai_var  = LoadOpenAIConfig()
neo4j_var = LoadNeo4jConfig()
uri = neo4j_var.get_uri()
user = neo4j_var.get_user()
password = neo4j_var.get_password()

AUTH = (str(user), str(password))
URI = str(uri)

def build_column_retrieval_query(table_name):
    return f"""
        WITH $queryVec AS queryVector
        MATCH  (n:RowValue)
        WHERE n.tableName = "{table_name}"
        RETURN 
            n, 
            vector.similarity.cosine(queryVector, n.rowValueEmbedding) AS similarity
        ORDER BY similarity DESC
        LIMIT 10;
        """


def create_array_from_string(input_string: str):
    array_to_process = []

    split_string = re.split(r'[\s,]+', input_string)  # Splits by space OR comma
    rprint(split_string)
    array_to_process.append(split_string)

    return array_to_process

def find_word_in_db(word: str):
    conn = db.get_db_connection()
    cur = conn.cursor()

    # Check if the word exists in the english_dict_openai_small table
    cur.execute("SELECT word FROM english_dict_openai_small WHERE word = %s", (word,))
    word_exists = cur.fetchone()

    cur.close()
    conn.close()

    if word_exists is None:
        return False
    else:
        return True

def insert_word_embedding_to_db(word: str, embedding: str):
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()

        # Create embedding for the word
        # embedding = create_embedding_for_word(word)

        cur.execute(
            "INSERT INTO english_dict_openai_small (word, embedding) VALUES (%s, %s)",
            (word, embedding)  # Pass values as a tuple
        )
        conn.commit()

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Unexpected error: {str(e)}")

def create_embedding_for_words(words: list):

    # Create embedding for the word
    embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=512
    )
    embedding = embeddings.embed_documents(words)
    rprint("Embedding created for words: ", words)
    return embedding


def get_embedding_for_word(word: str):
    conn = db.get_db_connection()
    cur = conn.cursor()

    # Check if the word exists in the english_dict_openai_small table
    cur.execute("SELECT embedding FROM english_dict_openai_small WHERE word = %s", (word,))
    embedding = cur.fetchone()

    cur.close()
    conn.close()

    return embedding

def get_word_and_embedding(word: str):
    conn = db.get_db_connection()
    cur = conn.cursor()

    # Check if the word exists in the english_dict_openai_small table
    cur.execute("SELECT word, embedding FROM english_dict_openai_small WHERE word = %s", (word,))
    word_and_embedding = cur.fetchone()

    cur.close()
    conn.close()

    return word_and_embedding

def process_string_return_similarity(input_string: str, table_name: str):
    rprint("input_string: ", input_string)
    result_array = []
    array_to_process = create_array_from_string(input_string)
    array_to_embed = []
    array_for_argument = []

    for word in array_to_process[0]:
        sql_result = get_word_and_embedding(word)
        if sql_result is None:
            array_to_embed.append(word)
        else:
            array_for_argument.append(sql_result)

    embeddings = create_embedding_for_words(array_to_embed)

    for word, embedding in zip(array_to_embed, embeddings):
        insert_word_embedding_to_db(word, embedding)
        sql_result = get_word_and_embedding(word)
        array_for_argument.append(sql_result)

    for sql_result in array_for_argument:
        pg_word = sql_result[0]
        pg_embedding = sql_result[1]
        rprint(f"pg_word: {pg_word}")
        
        if isinstance(pg_embedding, str):
            pg_embedding = ast.literal_eval(pg_embedding)

        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            with driver.session() as session:
                query = build_column_retrieval_query(table_name)
                results = session.run(query, queryVec=pg_embedding)
                for record in results:
                    result_array.append({
                        "columnName": record['n']['columnName'],
                        "value": record['n']['value'],
                        "similarity": record['similarity']
                    })

    result_array.sort(key=lambda x: x['similarity'], reverse=True)
    # for result in result_array:
    #     print(f"Column Name: {result['columnName']}, Value: {result['value']}, Similarity: {result['similarity']}")

    return result_array

def remove_duplicate_dicts(similar_rows):
    seen = set()
    unique_rows = []
    
    for row in similar_rows:
        key = (row['columnName'], row['value'])
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
            
    return unique_rows

        



# if __name__ == "__main__":
#     if len(sys.argv) > 1:
#         function_name = sys.argv[1]
#         if function_name == "process_string_return_similarity":
#             process_string_return_similarity(some_string)
#         else:
#             print(f"Function '{function_name}' not found.")
#     else:
#         print("Usage: python script.py <function_name>")