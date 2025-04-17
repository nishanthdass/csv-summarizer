from pydantic import BaseModel
from typing import Optional
from typing_extensions import Annotated, TypedDict
from typing import Sequence, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field 


class TableNameRequest(BaseModel):
    table_name: Optional[str] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 10 


class PdfNameRequest(BaseModel):
    pdf_name: Optional[str] = None

