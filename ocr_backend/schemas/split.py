from pydantic import BaseModel, root_validator, model_validator
from typing import List, Dict, Optional
from enum import Enum

class SplitType(str, Enum):
    EQUAL = "equal"
    CUSTOM = "custom"
    PROPORTIONAL = "proportional"
    ITEM_BASED = "item_based"
    ME_ONLY = "me_only"

class SplitRequest(BaseModel):
    split_type: SplitType
    users: List[str]
    # For CUSTOM split: {"Alice": 20.0, "Bob": 30.0}
    custom_shares: Optional[Dict[str, float]] = None
    # For ITEM_BASED: Map item_id to list of users sharing it
    item_assignments: Optional[Dict[int, List[str]]] = None
    
    @model_validator(mode='after')
    def validate_split(self):
        if self.split_type == SplitType.CUSTOM and not self.custom_shares:
            raise ValueError("custom_shares required for CUSTOM split")
        if self.split_type == SplitType.ITEM_BASED and not self.item_assignments:
            raise ValueError("item_assignments required for ITEM_BASED split")
        return self

class UserShareResponse(BaseModel):
    id: int
    user_name: str
    share_amount: float
    
    model_config = {"from_attributes": True}

