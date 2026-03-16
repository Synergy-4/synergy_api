from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Array of game type names completed in this session
    game_types = Column(JSONB, default=[])
    
    # e.g., {"matching": 80, "sorting": 100}
    scores = Column(JSONB, default={})
    
    # 1-5 rating from parent
    parent_rating = Column(Integer, nullable=True)
    
    completed = Column(Boolean, default=False)
    duration_seconds = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    child = relationship("Child", back_populates="sessions")
    activity = relationship("Activity")
