from rich import print as rprint
from db.tabular.table_operations import run_query
from rich import print as rprint


def sql_agent_function(table_name: str, query: str, role: str, query_type: str):
    """"""
    message_str = ""
    try:
        res = run_query(table_name, query, role, query_type)
        keys = list(res[0].keys())
        if len(keys) >= 1:
            for dict_res in res:
                for key in keys:
                    if key != "ctid":
                        message_str += key + ": " + str(dict_res[key]) + "<br/>"
                message_str += "<br/>"

        res = {"Result": message_str}
        return res
    except Exception as e:
        rprint(f"Query failed: {str(e)}")
        res = {"Error": str(e)}
        return res
