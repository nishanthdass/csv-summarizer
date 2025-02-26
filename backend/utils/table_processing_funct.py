def param_insert_csv(table_name, column_name, data_type):
    '''
    Format params for Neo4j query
    '''
    params = {
        'chunkParam': {
            'columnId': column_name+"_"+table_name,
            'tableName': table_name,
            'columnName': column_name,
            'columnType': data_type
        }
    }

    return params