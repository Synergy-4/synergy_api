from datetime import datetime
from pydantic import BaseModel

class AssetBase(BaseModel):
    name: str
    asset_type: str

class AssetOut(AssetBase):
    id: int
    path: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
