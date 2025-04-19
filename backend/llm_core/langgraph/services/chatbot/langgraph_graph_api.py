from llm_core.langgraph.models.models import MessageState
from langgraph.graph import START, StateGraph, END
from llm_core.langgraph.components.agents.agents import *


# --- Build the SQL State Graph ---
workflow_sql = StateGraph(state_schema=MessageState)

# Nodes
workflow_sql.add_node("sql_agent", sql_agent_node)
workflow_sql.add_node("human_input", human_input)

# Edges
workflow_sql.add_edge(START, "sql_agent")
workflow_sql.add_edge("sql_agent", END)
workflow_sql.add_edge("human_input", "sql_agent")

# --- Build the PDF State Graph ---
workflow_pdf = StateGraph(state_schema=MessageState)

# Nodes
workflow_pdf.add_node("pdf_agent", pdf_agent_node)
workflow_pdf.add_node("human_input", human_input)

# Edges
workflow_pdf.add_edge(START, "pdf_agent")
workflow_pdf.add_edge("pdf_agent", END)
workflow_pdf.add_edge("human_input", "pdf_agent")

# --- Build the Multiagent State Graph ---
workflow_multi = StateGraph(state_schema=MessageState)

# # Nodes
workflow_multi.add_node("sql_agent", sql_agent_node)
workflow_multi.add_node("data_analyst", data_analyst_node)
workflow_multi.add_node("human_input", human_input)
# # Edges
workflow_multi.add_edge(START, "data_analyst")
workflow_multi.add_edge("data_analyst", END)
workflow_multi.add_edge("sql_agent", END)
workflow_multi.add_edge("human_input", "sql_agent")

workflow_multi.add_conditional_edges("data_analyst", lambda state: state["next_agent"])