
from models.models import MessageState
from langgraph.graph import START, StateGraph, END
from llm_core.src.llm.agents import *


# --- Build the State Graph ---
workflow = StateGraph(state_schema=MessageState)

# Nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("pdf_agent", pdf_agent_node)
workflow.add_node("sql_agent", sql_agent_node)
workflow.add_node("sql_manipulator_agent", sql_manipulator_agent_node)
workflow.add_node("data_analyst", data_analyst_node)
workflow.add_node("human_input", human_input)
workflow.add_node("cleanup", cleanup_node)
# Edges
workflow.add_edge(START, "supervisor")
workflow.add_edge("sql_agent", END)
workflow.add_edge("sql_manipulator_agent", END)
# workflow.set_finish_point("sql_agent")
workflow.add_edge("pdf_agent", END)
# workflow.set_finish_point("pdf_agent")
workflow.add_edge("data_analyst", END)
workflow.add_edge("pdf_agent", "data_analyst")
workflow.add_edge("sql_agent", "data_analyst")
workflow.add_edge("human_input", "data_analyst")
workflow.set_finish_point("data_analyst")


workflow.add_conditional_edges("supervisor", lambda state: state["next_agent"])
workflow.add_conditional_edges("data_analyst", lambda state: state["next_agent"])


# --- Build the SQL State Graph ---
workflow_sql = StateGraph(state_schema=MessageState)

# Nodes
workflow_sql.add_node("sql_agent", sql_agent_node)
workflow_sql.add_node("human_input", human_input)

# Edges
workflow_sql.add_edge(START, "sql_agent")
workflow_sql.add_edge("sql_agent", END)
workflow_sql.add_edge("human_input", "sql_agent")
# workflow_sql.add_conditional_edges("sql_agent", lambda state: state["next_agent"])
# workflow_sql.add_conditional_edges("human_input", lambda state: state["next_agent"])
