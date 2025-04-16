import re
from config import neo4j_var, postgres_var
import psycopg2


uri = neo4j_var.get_uri()
user = neo4j_var.get_user()
password = neo4j_var.get_password()

AUTH = (str(user), str(password))
URI = str(uri)


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