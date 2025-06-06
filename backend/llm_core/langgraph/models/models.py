from pydantic import BaseModel
from typing import Optional
from typing_extensions import Annotated, TypedDict
from typing import Sequence, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field 


class MessageInstance(BaseModel):
    """Schema for message."""
    role: Optional[str] = None                      # name of the agent that sent the message
    table_name: Optional[str] = None                # name of table associated with the message
    pdf_name: Optional[str] = None                  # name of pdf associated with the message
    event: Optional[str] = None                     # event type from chat stream
    message: Optional[str] = None                   # message from chat stream
    time: Optional[float] = None                    # processing time
    input_tokens: Optional[int] = None              # input tokens used
    output_tokens: Optional[int] = None             # output tokens used
    total_tokens: Optional[int] = None              # total tokens used
    run_id: Optional[str] = None                    # run id from chat stream
    thread_id: Optional[str] = None                 # thread id created by chat manager upon initialization
    has_function_call: Optional[bool] = None        # whether the message contains a function call
    tool_call_name: Optional[str] = None            # tool call used to generate results
    model_name: Optional[str] = None                # model name used to generate results
    answer_retrieval_query: Optional[str] = None    # query that answers the question
    visualizing_query: Optional[str] = None         # query thatn visualizes the answer
    viewing_query_label: Optional[str] = None       # label for the visualization
    query_type: Optional[str] = None                # query type (retrieval or manipulation)
   

class MessageState(TypedDict):
    """Schema for state."""
    current_agent: str
    next_agent: str
    question: str
    augmented_question: str
    answer: str
    table_name: str
    table_relevant_data: str
    pdf_name: str
    pdf_relevant_data: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    agent_scratchpads: list
    answer_retrieval_query: str
    visualizing_query: str
    viewing_query_label: str
    query_type: str
    is_multiagent: bool
    agent_step: int
    runtime_queries: str
    query_failed: str
    

class SQL_RETRIEVAL_AGENT_JSON_TEMPLATE(BaseModel):
    current_agent: str = Field(description="sql_agent")
    next_agent: str = Field(description="__end__ or human_input")
    question: str = Field(description="None")
    answer: str = Field(description="<_START_> Description of created query and why its the best query to answer the question. "
                                    "If the query fails, then share the answer query that failed verbatim in the answer, explain "
                                    "the reason why it failed, provide suggestions for a different query and wait for the user to "
                                    "respond <_END_>")
    query_type: str = Field(description="retrieval or __reevaluate__(if the user changes the subject of the conversation)")
    answer_retrieval_query: str = Field(description="Either a Failed Query or a Retrieval Query that answers the question and is successfully tested. Do not include any other information.")
    visualize_retrieval_query: str = Field(description="Query that visualizes the answer (has ctids). Do not include any other information.")
    visualize_retrieval_label: str = Field(description="Label that describes the visualize_retrieval_query. Do not include any other information.")


class SQL_MANIPULATION_AGENT_JSON_TEMPLATE(BaseModel):
    current_agent: str = Field(description="sql_agent")
    next_agent: str = Field(description="__end__")
    question: str = Field(description="None")
    answer: str = Field(description="<_START_> Description of created query and why its the best query to manipulate the database. "
                                    "If you could not create a manipulation query, explain the reason why in detail and wait for the user to respond <_END_>")
    query_type: str = Field(description="retrieval or __reevaluate__(if the user changes the subject of the conversation)")
    perform_manipulation_query: str = Field(description="Query that alters the database or data. Do not include any other information.")
    perform_manipulation_label: str = Field(description="Label that describes the perform_manipulation_query. Do not include any other information.")


class PDF_KG_RETRIEVE_TEMPLATE(BaseModel):
    answer: str = Field(description= "<_START_> Your complete answer <_END_>")
    data_points: str = Field(description="most relevant data points such as addresses, names, dates, emails, etc")
    sources: str = Field(description="most relevant page number and line number")


class Route(BaseModel):
    """Schema for routing a question to an agent."""
    current_agent: str = Field(description="name of the current agent")
    next_agent: str = Field(description="name of the agent to route the question to")
    question: str = Field(description="question to route to the agent")
    answer: Optional[str] = Field(default=None, description="answer to the question, if answer is not ready yet then None")
    competed_step: Optional[int] = Field(default=None, description="step that the agent has completed")


class DataAnalystResponse(BaseModel):
    """Model for the data analyst's JSON response."""
    current_agent: str = Field(description="data_analyst")
    next_agent: str = Field(description="sql_agent")
    question: str = Field(description="The initial question.")
    augmented_question: str = Field( description="The augmented question with numerical and/or textual table data that can help answer the question")
    table_data_points: str = Field(description="Supporting table data that can help write an accurate sql query. More is better")
