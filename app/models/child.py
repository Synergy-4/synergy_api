from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    age_in_years = Column(Integer, nullable=False)
    interests = Column(JSONB, nullable=True)  # Store as a list of strings
    diagnosis_notes = Column(String, nullable=True) # Encrypt later if necessary

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("User", backref="children")
    goals = relationship("Goal", back_populates="child", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="child", cascade="all, delete-orphan")
