from pydantic import BaseModel

class TableNameRequest(BaseModel):
    table_name: str
    page: int = 1  # Default to page 1
    page_size: int = 10  # Default page size is 10 rows