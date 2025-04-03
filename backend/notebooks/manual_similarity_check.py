

def get_word_and_embedding(word: str):
    conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
    cur = conn.cursor()

    # Check if the word exists in the english_dict_openai_small table
    cur.execute("SELECT word, embedding FROM english_dict_openai_small WHERE word = %s", (word,))
    word_and_embedding = cur.fetchone()

    cur.close()
    conn.close()

    return word_and_embedding


def insert_word_embedding_to_db(word: str, embedding: str):
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
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
    openai_api_key=OPENAI_API_KEY,
    openai_api_base=OPENAI_BASE_URL,
    model=OPENAI_EMB_MODEL_SMALL,
    dimensions=512
    )
    embedding = embeddings.embed_documents(words)
    return embedding



def add_to_embedding_dict(input_string: str):
    result_array = []
    array_to_process = re.split(r'[\s,]+', input_string)
    array_to_embed = []
    word_embeddings = {}

    # check if word is embedded in embedding dictionary
    for word in array_to_process:
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


def find_similarity(embedding):
    try:
        connection = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        cur = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        sql = """
            SELECT *, embedding <-> %s AS l2_dist
            FROM langchain_pg_embedding
            ORDER BY embedding <=> %s
            LIMIT 10;
        """
        # Note: you need to pass the embedding twice (for SELECT and ORDER BY)
        cur.execute(sql, (embedding, embedding))

        results = cur.fetchall()
        return results

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None

    finally:
        if cur:
            cur.close()
        if connection:
            connection.close()
