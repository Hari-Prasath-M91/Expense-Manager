from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from backend.schemas.item import LineItemResponse
from backend.schemas.split import UserShareResponse

class LineItemUpdate(BaseModel):
    id: int
    description: str
    amount: float

class ExpenseUpdate(BaseModel):
    merchant: str
    date: str
    category: str
    total_amount: float
    cgst: float
    sgst: float
    additional_charge: float

class OCRMetricsBase(BaseModel):
    cer: Optional[float] = None
    wer: Optional[float] = None
    processing_time: float

class OCRMetricsResponse(OCRMetricsBase):
    id: int
    expense_id: int
    
    model_config = {"from_attributes": True}

class ExpenseBase(BaseModel):
    merchant: Optional[str] = None
    date: Optional[str] = None
    total_amount: Optional[float] = None
    cgst: Optional[float] = 0.0
    sgst: Optional[float] = 0.0
    additional_charge: Optional[float] = 0.0
    category: Optional[str] = None
    confidence: Optional[float] = None

class ExpenseCreate(ExpenseBase):
    items: List[dict] = [] # Used when creating

class ExpenseResponse(ExpenseBase):
    id: int
    created_at: datetime
    line_items: List[LineItemResponse] = []
    user_shares: List[UserShareResponse] = []
    ocr_metrics: Optional[OCRMetricsResponse] = None

    model_config = {"from_attributes": True}
    
class ExpenseSummaryResponse(ExpenseBase):
    id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}
