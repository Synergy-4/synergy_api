from typing import Optional, List
from pydantic import BaseModel

class GoalBase(BaseModel):
    domain: str
    description: str
    priority: Optional[int] = 1
    is_active: Optional[bool] = True

class GoalCreate(GoalBase):
    pass

class GoalUpdate(GoalBase):
    domain: Optional[str] = None
    description: Optional[str] = None

class GoalInDBBase(GoalBase):
    id: int
    child_id: int

    class Config:
        from_attributes = True

class Goal(GoalInDBBase):
    pass
