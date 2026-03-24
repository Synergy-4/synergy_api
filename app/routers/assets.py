from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os

from app.core.database import get_db
from app.models.asset import Asset

router = APIRouter()

# Base directory for WebP assets (mirrors the same subfolder structure as the PNG assets)
_WEBP_BASE = os.path.join(os.path.dirname(__file__), "..", "assets_webp", "assets")


def _resolve_path(relative_path: str) -> str:
    """Resolve a relative asset path (e.g. 'clothes/suit.webp') to its absolute WebP path."""
    return os.path.normpath(os.path.join(_WEBP_BASE, relative_path))


@router.get("/{asset_type}/{name}")
async def get_asset(
    asset_type: str,
    name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve an asset file by its type and name (serves WebP when available).
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

    # Resolve the relative path stored in the DB against the WebP assets directory
    file_path = _resolve_path(asset.path)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/webp")

    raise HTTPException(status_code=404, detail=f"Asset file not found: {asset.path}")
