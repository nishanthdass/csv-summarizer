from pydantic import BaseModel
from typing import List, Optional, Dict
from typing_extensions import Annotated, TypedDict
from typing import Sequence, Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage, AIMessageChunk
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class MessageInstance(BaseModel):
    role: Optional[str] = None
    table_name: Optional[str] = None
    pdf_name: Optional[str] = None
    event: Optional[str] = None
    message: Optional[str] = None
    time: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    run_id: Optional[str] = None
    thread_id: Optional[str] = None
    tool_call_name: Optional[str] = None
    model_name: Optional[str] = None
    answer_retrieval_query: Optional[str] = None
    visualizing_query: Optional[str] = None
    viewing_query_label: Optional[str] = None
    has_function_call: Optional[bool] = None
    
    


class TableNameRequest(BaseModel):
    table_name: Optional[str] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 10 


class PdfNameRequest(BaseModel):
    pdf_name: Optional[str] = None

class MessageState(TypedDict):
    """Schema for state."""
    current_agent: str
    next_agent: str
    question: str
    answer: str
    table_name: str
    pdf_name: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    agent_scratchpads: list
    columns_and_types: str
    answer_retrieval_query: str
    visualizing_query: str
    viewing_query_label: str
    is_multiagent: bool
    agent_step: int
    runtime_queries: str
    query_failed: str
    


class Route(BaseModel):
    """Schema for routing a question to an agent."""
    current_agent: str = Field(description="name of the current agent")
    next_agent: str = Field(description="name of the agent to route the question to")
    question: str = Field(description="question to route to the agent")
    answer: Optional[str] = Field(default=None, description="answer to the question, if answer is not ready yet then None")
    competed_step: Optional[int] = Field(default=None, description="step that the agent has completed")