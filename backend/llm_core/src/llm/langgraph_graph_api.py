
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


# --- Build the PDF State Graph ---
workflow_pdf = StateGraph(state_schema=MessageState)

# Nodes
workflow_pdf.add_node("pdf_agent", pdf_agent_node)
workflow_pdf.add_node("human_input", human_input)

# Edges
workflow_pdf.add_edge(START, "pdf_agent")
workflow_pdf.add_edge("pdf_agent", END)
workflow_pdf.add_edge("human_input", "pdf_agent")
# workflow_pdf.add_conditional_edges("pdf_agent", lambda state: state["next_agent"])
# workflow_pdf.add_conditional_edges("human_input", lambda state: state["next_agent"])


# --- Build the Multiagent State Graph ---
workflow_multi = StateGraph(state_schema=MessageState)

# # Nodes
workflow_multi.add_node("pdf_agent", pdf_agent_node)
workflow_multi.add_node("sql_agent", sql_agent_node)
workflow_multi.add_node("data_analyst", data_analyst_node)
workflow_multi.add_node("human_input", human_input)
# # Edges
workflow_multi.add_edge(START, "data_analyst")
workflow_multi.add_edge("data_analyst", END)
workflow_multi.add_edge("sql_agent", END)
workflow_multi.add_edge("pdf_agent", END)

workflow_multi.add_edge("pdf_agent", "data_analyst")
workflow_multi.add_edge("sql_agent", "data_analyst")
workflow_multi.add_edge("human_input", "data_analyst")

workflow_multi.add_conditional_edges("data_analyst", lambda state: state["next_agent"])

# # Nodes
# workflow_multi.add_node("data_analyst", data_analyst_node)
# workflow_multi.add_node("tools", tool_node)

# # Set the entrypoint as `agent`
# # This means that this node is the first one called
# workflow_multi.set_entry_point("data_analyst")

# # We now add a conditional edge
# workflow_multi.add_conditional_edges(
#     # First, we define the start node. We use `agent`.
#     # This means these are the edges taken after the `agent` node is called.
#     "data_analyst",
#     # Next, we pass in the function that will determine which node is called next.
#     should_continue,
#     # Finally we pass in a mapping.
#     # The keys are strings, and the values are other nodes.
#     # END is a special node marking that the graph should finish.
#     # What will happen is we will call `should_continue`, and then the output of that
#     # will be matched against the keys in this mapping.
#     # Based on which one it matches, that node will then be called.
#     {
#         # If `tools`, then we call the tool node.
#         "continue": "tools",
#         # Otherwise we finish.
#         "end": END,
#     },
# )

# # We now add a normal edge from `tools` to `agent`.
# # This means that after `tools` is called, `agent` node is called next.
# workflow.add_edge("tools", "data_analyst")