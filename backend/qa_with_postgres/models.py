from pydantic import BaseModel
from typing import List, Optional, Dict

class TableNameRequest(BaseModel):
    table_name: str
    page: int = 1  # Default to page 1
    page_size: int = 10  # Default page size is 10 rows

class TableSummaryDataRequest(BaseModel):
    table_name: str
    total_table_row_size: Optional[int] = None
    total_sample_row_size: Optional[int] = None
    results: Optional[Dict] = None