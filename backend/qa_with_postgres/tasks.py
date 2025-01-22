from typing import List, Dict, Any

tables: Dict[str, Dict[str, Any]] = {}

def add_table(table_name):
    if table_name in tables:
        raise ValueError("Table already exists.")
    tables[table_name] = {
        "tasks": [],
    }

def delete_task_table(table_name):
    if table_name not in tables:
        return
    del tables[table_name]

def add_task(table_name, task_id, description):
    if table_name not in tables:
        raise ValueError("Table not found.")
    tables[table_name]["tasks"].append({
        "task_id": task_id,
        "description": description,
        "status": "Not Started",
        "result": None
    })

def update_task(table_name, task_id, status, result=None):
    if table_name not in tables:
        raise ValueError("Table not found.")
    for task in tables[table_name]["tasks"]:
        if task["task_id"] == task_id:
            task["status"] = status
            task["result"] = result
            return
    raise ValueError("Task not found.")

def get_tasks_for_table(table_name):
    if table_name not in tables:
        raise ValueError("Table not found.")
    return tables[table_name]["tasks"]

def get_task(table_name, task_id):
    if table_name not in tables:
        raise ValueError("Table not found.")
    for task in tables[table_name]["tasks"]:
        if task["task_id"] == task_id:
            task["table_name"] = table_name
            return task
        

        
def delete_task(table_name, task_id):
    if table_name not in tables:
        raise ValueError("Table not found.")
    for task in tables[table_name]["tasks"]:
        if task["task_id"] == task_id:
            tables[table_name]["tasks"].remove(task)
            return
