from db.db_utility import get_all_columns_and_types, run_query


def sql_agent_function(table_name: str, query: str):
    message_str = ""
    res = run_query(table_name, query)
    keys = list(res[0].keys())
    if len(keys) > 1:
        for dict_res in res:
            for key in keys:
                if key != "ctid":
                    message_str += key + ": " + str(dict_res[key]) + "<br/>"
            message_str += "<br/>"

    return message_str


