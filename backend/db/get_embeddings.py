import re
from rich import print as rprint
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph
from neo4j import GraphDatabase
from config import openai_var, neo4j_var, postgres_var
from db.structured.postgres_utils import get_all_columns_and_types
import ast
import psycopg2


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
    conn = postgres_var.get_db_connection()
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
        conn = postgres_var.get_db_connection()
        cur = conn.cursor()

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
    return embedding


def create_embedding_for_line(line: str):
    embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=512
    )
    embedding = embeddings.embed_query(line)
    return embedding


def get_embedding_for_word(word: str):
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    # Check if the word exists in the english_dict_openai_small table
    cur.execute("SELECT embedding FROM english_dict_openai_small WHERE word = %s", (word,))
    embedding = cur.fetchone()

    cur.close()
    conn.close()

    return embedding

def get_word_and_embedding(word: str):
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    # Check if the word exists in the english_dict_openai_small table
    cur.execute("SELECT word, embedding FROM english_dict_openai_small WHERE word = %s", (word,))
    word_and_embedding = cur.fetchone()

    cur.close()
    conn.close()

    return word_and_embedding

def add_to_embedding_dict(input_string: str, table_name: str):
    rprint("input_string: ", input_string)
    result_array = []
    array_to_process = create_array_from_string(input_string)
    array_to_embed = []
    word_embeddings = {}

    # check if word is embedded in embedding dictionary
    for word in array_to_process[0]:
        sql_result = get_word_and_embedding(word)
        if sql_result is None:
            array_to_embed.append(word)
        else:
            word_embeddings[word] = sql_result

    embeddings = create_embedding_for_words(array_to_embed)

    # insert word embedding to database
    for word, embedding in zip(array_to_embed, embeddings):
        insert_word_embedding_to_db(word, embedding)
        sql_result = get_word_and_embedding(word)
        word_embeddings[word] = sql_result

    return word_embeddings



def create_embedding_for_word(word: str):
    # Create embedding for the word
    embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=3072
    )
    embedding = embeddings.embed_query(word)

    return embedding


def insert_word_to_db(word: str):
    try:
        conn = postgres_var.get_db_connection()
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


def process_string_return_similarity(input_string: str, table_name: str):
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
    return result_array


def get_similar_rows(table_name: str, words: str):
    """Get similar rows from table based on word and levenshtein distance. 
    Returns: list of tuples (word, column_name, column_value, lev_distance)"""

    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    words_list = re.split(r"[,\s]+", words.strip())


    columns_and_types = get_all_columns_and_types(table_name)  # Returns List[Tuple[column_name, type]]

    results = []

    for word in words_list:
        query_parts = []

        for column_name, _ in columns_and_types:
            # Skip numeric columns or ones that can't be cast to text, if needed
            query_parts.append(f"""
                SELECT '{column_name}' AS column_name,
                       {column_name}::text AS column_value,
                       levenshtein({column_name}::text, %s) AS lev_distance
                FROM {table_name}
            """)

        # Combine all column queries with UNION ALL
        final_query = " UNION ALL ".join(query_parts) + " ORDER BY lev_distance LIMIT 15;"

        cur.execute(final_query, (word,) * len(columns_and_types))
        rows = cur.fetchall()
        for row in rows:
            results.append((word, *row))  # tuple: (word, column_name, column_value, lev_distance)

    seen = set()
    unique_results = []
    for result in results:
        if result not in seen:
            seen.add(result)
            unique_results.append(result)

    filtered_results = [r for r in unique_results if r[3] <= 5]

    sorted_results = sorted(filtered_results, key=lambda x: x[3])

    sorted_results = [result[1:] for result in sorted_results]

    cur.close()
    conn.close()
    return sorted_results


def remove_duplicate_dicts(similar_rows):
    seen = set()
    unique_rows = []
    
    for row in similar_rows:
        key = (row['columnName'], row['value'])
        if key not in seen:
            seen.add(key)
            unique_rows.append(row)
            
    return unique_rows


def levenshtein_dist_from_db(table_name: str, words: str):
    """ Counts how many single-character edits (insertion, deletion, substitution) it takes to transform one string into another.
        It has no understanding of meaning, context, or semantics — it’s purely syntactic."""

    try:
        connection = postgres_var.get_db_connection()
        cur = connection.cursor()
    
        words_list = re.split(r"[,\s]+", words.strip())
    
        columns_and_types = get_all_columns_and_types(table_name)
    
        results = []

        for word in words_list:
            query_parts = []
    
            for column_name, _ in columns_and_types:
                query_parts.append(f"""
                    SELECT '{column_name}' AS column_name,
                           {column_name}::text AS column_value,
                           levenshtein({column_name}::text, %s) AS lev_distance
                    FROM {table_name}
                """)
    
            # Combine all column queries with UNION ALL
            final_query = " UNION ALL ".join(query_parts) + " ORDER BY lev_distance LIMIT 30;"
    
            cur.execute(final_query, (word,) * len(columns_and_types))
            rows = cur.fetchall()
            for row in rows:
                results.append((word, *row))
    
        seen = set()
        unique_results = []
        for result in results:
            if result not in seen:
                seen.add(result)
                unique_results.append(result)

        filtered_results = [
            r for r in unique_results
        ]

        sorted_results = sorted(filtered_results, key=lambda x: x[3])
    
        sorted_results = [result[1:] for result in sorted_results]

        cur.close()
        connection.close()

        return sorted_results

    except psycopg2.DatabaseError as e:
        print(f"Error: {str(e)}")
        return []