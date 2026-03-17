from typing import Optional, List
from datetime import date
from pydantic import BaseModel
from app.schemas.goal import Goal

class ChildBase(BaseModel):
    name: str
    date_of_birth: date
    interests: Optional[List[str]] = []
    diagnosis_notes: Optional[str] = None

class ChildCreate(ChildBase):
    pass

class ChildUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    interests: Optional[List[str]] = None
    diagnosis_notes: Optional[str] = None

class ChildInDBBase(ChildBase):
    id: int
    parent_id: int

    class Config:
        from_attributes = True

class Child(ChildInDBBase):
    goals: List[Goal] = []
