from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    path = Column(String, nullable=False, unique=True)
    asset_type = Column(String, nullable=False, index=True) # e.g., 'fruit'

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
