from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.schemas.activity import Activity

class SessionBase(BaseModel):
    game_types: Optional[List[str]] = []
    scores: Optional[Dict[str, int]] = {}
    parent_rating: Optional[int] = None
    completed: Optional[bool] = False
    duration_seconds: Optional[int] = None

class SessionCreate(SessionBase):
    child_id: int
    activity_id: int

class SessionUpdate(SessionBase):
    pass

class SessionInDBBase(SessionBase):
    id: int
    child_id: int
    activity_id: int

    class Config:
        from_attributes = True

class Session(SessionInDBBase):
    activity: Optional[Activity] = None
