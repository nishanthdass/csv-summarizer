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

def param_insert_csv_row_values(table_name, column_name, row_value, index):
    '''
    Format params for Neo4j query
    '''

    params = {
        'chunkParam': {
            'rowValueId': column_name +"_"+table_name + "_" + str(index),
            'tableName': table_name,
            'columnName': column_name,
            'value': row_value,
            'rowIndex': str(index)
        }
    }

    return params

def param_insert_csv_row_index(table_name, column_name, row_value, index):
    '''
    Format params for Neo4j query
    '''

    params = {
        'chunkParam': {
            'rowIndexId': column_name +"_"+table_name + "_" + str(index),
            'rowIndex': str(index)
        }
    }

    return params