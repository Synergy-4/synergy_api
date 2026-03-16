from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Store the full SDUI ActivityPayload as JSON
    ui_config = Column(JSONB, nullable=False)
    
    # Metadata for filtering/tracking
    ai_generated = Column(Boolean, default=True)
    theme_id = Column(String, nullable=False)
    game_types = Column(JSONB, nullable=True) # array of game types contained in this activity

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    child = relationship("Child")
