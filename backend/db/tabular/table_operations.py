from config import postgres_var
from fastapi import HTTPException
import psycopg2
from db.tabular.postgres_utilities import convert_postgres_to_react, get_all_columns_and_types
from utils.os_re_tools import split_words_by_commas_and_spaces

def run_query(table_name: str, query: str, role: str, query_type: str)-> list[str]:
    """
    Runs a query on a table and returns the results as a list of strings.
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT to_regclass('{table_name}')")
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")
    
    filtered_llm_query_result = []
    
    if query_type == "retrieval":
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}';")
        
        cur.execute(query)
        columns = cur.description
        values = cur.fetchall()

        llm_query_result = [dict(zip([col[0] for col in columns if col], row)) for row in values]

        for row in llm_query_result:
            filtered_llm_query_result.append(row)
             
    if query_type == "manipulation":
        cur.execute(query)
        conn.commit()

    return filtered_llm_query_result



def levenshtein_dist(table_name: str, words: str):
    """ Counts how many single-character edits (insertion, deletion, substitution) it takes to transform one string into another.
        It has no understanding of meaning, context, or semantics — it’s purely syntactic."""

    try:
        connection = postgres_var.get_db_connection()
        cur = connection.cursor()
    
        words_list = split_words_by_commas_and_spaces(words)
    
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
    

def get_table_data(table_name: str, page: int, page_size: int):
    """
    Fetches data from a table and returns it as a list of dictionaries.
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()

    # Check if table exists
    cur.execute(f"SELECT to_regclass(%s)", (table_name,))
    table_exists = cur.fetchone()[0]
    if not table_exists:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found.")

    # Get primary key column
    cur.execute(f"""
        SELECT a.attname
        FROM   pg_index i
        JOIN   pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE  i.indrelid = %s::regclass AND i.indisprimary;
    """, (table_name,))
    primary_keys = {row[0] for row in cur.fetchall()}

    # Get all column names and primary key
    cur.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s;
    """, (table_name,))
    all_columns = [row[0] for row in cur.fetchall()]
    selected_columns = [col for col in all_columns if col not in primary_keys]

    # Get column names and types for header (excluding embedding and primary key)
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s;
    """, (table_name,))
    all_column_types = cur.fetchall()
    filtered_column_types = [(col, dtype) for col, dtype in all_column_types if col not in primary_keys]
    columns_and_types = convert_postgres_to_react(filtered_column_types)

    # Total rows
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    total_rows = cur.fetchone()[0]
    offset = (page - 1) * page_size

    # Fetch paginated rows (exclude primary key & embedding)
    column_list = ", ".join(selected_columns) + ", ctid"
    cur.execute(f"""
        SELECT {column_list}
        FROM {table_name}
        LIMIT %s OFFSET %s
    """, (page_size, offset))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    # Build the table object
    table_data = {
        "header": {col_name: col_type for col_name, col_type in columns_and_types},
        "rows": [dict(zip(columns, row)) for row in rows],
        "page": page,
        "page_size": page_size,
        "total_rows": total_rows,
        "total_pages": (total_rows + page_size - 1) // page_size
    }

    return table_data


def delete_table(table_name: str):
    """
    Deletes a table from the database.
    Does not delete embeddings from vector store
    """
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete table")
    cur.close()
    conn.close()

    return {"message": f"Table {table_name} deleted successfully."}
    

def get_table_names_from_db():
    conn = postgres_var.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.relname AS table_name
            FROM pg_class c
            JOIN pg_description d ON c.oid = d.objoid
            WHERE c.relkind = 'r'  -- 'r' stands for ordinary table
            AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            AND d.description = 'source_type: csv';
        """)
        files = [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    cur.close()
    conn.close()

    return files