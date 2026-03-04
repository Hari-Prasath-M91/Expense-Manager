from pydantic import BaseModel
from typing import List, Optional
from backend.schemas.expense import ExpenseSummaryResponse

class SearchRequest(BaseModel):
    query: Optional[str] = None # Free text
    merchant: Optional[str] = None
    category: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[ExpenseSummaryResponse]
    total_count: int
