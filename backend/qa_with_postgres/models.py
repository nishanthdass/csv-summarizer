from pydantic import BaseModel
from typing import List, Optional, Dict

class TableNameRequest(BaseModel):
    table_name: Optional[str] = None
    page: Optional[int] = 1
    page_size: Optional[int] = 10 


class PdfNameRequest(BaseModel):
    pdf_name: Optional[str] = None