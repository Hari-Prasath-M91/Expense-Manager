from pydantic import BaseModel
from typing import Optional

class LineItemBase(BaseModel):
    description: str
    amount: float
    user_assigned: Optional[str] = None

class LineItemCreate(LineItemBase):
    pass

class LineItemResponse(LineItemBase):
    id: int
    expense_id: int

    model_config = {"from_attributes": True}
