from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os

from app.core.database import get_db
from app.models.asset import Asset
from app.schemas.asset import AssetOut

router = APIRouter()

@router.get("/{asset_type}/{name}")
async def get_asset(
    asset_type: str,
    name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve an asset file by its type and name.
    Example: GET /api/v1/assets/fruit/apple
    """
    stmt = select(Asset).where(
        Asset.asset_type == asset_type,
        Asset.name == name
    )
    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    if not os.path.exists(asset.path):
        raise HTTPException(status_code=404, detail=f"Asset file not found at {asset.path}")
    
    return FileResponse(asset.path)
