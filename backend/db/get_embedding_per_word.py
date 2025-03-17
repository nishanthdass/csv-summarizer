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
        LIMIT 5;
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

    # Check if the word exists in the english_dict_openai_large table
    cur.execute("SELECT word FROM english_dict_openai_large WHERE word = %s", (word,))
    word_exists = cur.fetchone()

    cur.close()
    conn.close()

    if word_exists is None:
        return False
    else:
        return True

def insert_word_to_db(word: str):
    try:
        conn = db.get_db_connection()
        cur = conn.cursor()

        # Create embedding for the word
        embedding = create_embedding_for_word(word)

        cur.execute(
            "INSERT INTO english_dict_openai_large (word, embedding) VALUES (%s, %s)",
            (word, embedding)  # Pass values as a tuple
        )
        conn.commit()

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Unexpected error: {str(e)}")

def create_embedding_for_word(word: str):

    # Create embedding for the word
    embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=3072
    )
    embedding = embeddings.embed_query(word)
    rprint("embedding created: ", embedding)

    return embedding


def get_embedding_for_word(word: str):
    conn = db.get_db_connection()
    cur = conn.cursor()

    # Check if the word exists in the english_dict_openai_large table
    cur.execute("SELECT embedding FROM english_dict_openai_large WHERE word = %s", (word,))
    embedding = cur.fetchone()

    cur.close()
    conn.close()

    return embedding

def get_word_and_embedding(word: str):
    conn = db.get_db_connection()
    cur = conn.cursor()

    # Check if the word exists in the english_dict_openai_large table
    cur.execute("SELECT word, embedding FROM english_dict_openai_large WHERE word = %s", (word,))
    word_and_embedding = cur.fetchone()

    cur.close()
    conn.close()

    return word_and_embedding

def process_string_return_similarity(input_string: str, table_name: str):
    rprint("input_string: ", input_string)
    result_array = []
    array_to_process = create_array_from_string(input_string)

    for word in array_to_process[0]:
        sql_result = get_word_and_embedding(word)
        if sql_result is None:
            insert_word_to_db(word)
            sql_result = get_word_and_embedding(word)

        pg_word = sql_result[0]
        pg_embedding = sql_result[1]
        
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


        



# if __name__ == "__main__":
#     if len(sys.argv) > 1:
#         function_name = sys.argv[1]
#         if function_name == "process_string_return_similarity":
#             process_string_return_similarity(some_string)
#         else:
#             print(f"Function '{function_name}' not found.")
#     else:
#         print("Usage: python script.py <function_name>")