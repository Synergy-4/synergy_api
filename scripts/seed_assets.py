import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to sys.path so `app` is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset

# Base directory — each subdirectory is an asset_type
ASSETS_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    "app", "assets_webp", "assets"
)

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


async def seed_assets():
    async with AsyncSessionLocal() as session:
        total_added = 0

        # Each subdirectory name becomes the asset_type
        for asset_type in sorted(os.listdir(ASSETS_BASE_DIR)):
            type_dir = os.path.join(ASSETS_BASE_DIR, asset_type)
            if not os.path.isdir(type_dir):
                continue

            files = [f for f in os.listdir(type_dir) if f.lower().endswith(SUPPORTED_EXTENSIONS)]
            print(f"\n[{asset_type}] Found {len(files)} file(s)")

            for filename in sorted(files):
                name = os.path.splitext(filename)[0]
                path = os.path.join(asset_type, filename)  # relative: e.g. "clothes/suit.webp"

                stmt = select(Asset).where(Asset.name == name, Asset.asset_type == asset_type)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if not existing:
                    print(f"  + Adding: {asset_type}/{name}")
                    session.add(Asset(name=name, path=path, asset_type=asset_type))
                    total_added += 1
                elif existing.path != path:
                    print(f"  ~ Updating path: {asset_type}/{name} ({existing.path!r} -> {path!r})")
                    existing.path = path
                else:
                    print(f"  ~ Skipping (exists): {asset_type}/{name}")

        await session.commit()
        print(f"\nDone. {total_added} asset(s) added.")


if __name__ == "__main__":
    asyncio.run(seed_assets())
