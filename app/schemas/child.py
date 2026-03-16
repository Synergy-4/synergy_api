from typing import Optional, List
from pydantic import BaseModel
from app.schemas.goal import Goal

class ChildBase(BaseModel):
    name: str
    age_in_years: int
    interests: Optional[List[str]] = []
    diagnosis_notes: Optional[str] = None

class ChildCreate(ChildBase):
    pass

class ChildUpdate(ChildBase):
    name: Optional[str] = None
    age_in_years: Optional[int] = None

class ChildInDBBase(ChildBase):
    id: int
    parent_id: int

    class Config:
        from_attributes = True

class Child(ChildInDBBase):
    goals: List[Goal] = []
