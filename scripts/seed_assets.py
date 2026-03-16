import asyncio
import os
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add the project directory to the sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset

FRUIT_ASSETS_DIR = "app/assets/fruits"

async def seed_fruits():
    async with AsyncSessionLocal() as session:
        # Get all fruit files
        files = [f for f in os.listdir(FRUIT_ASSETS_DIR) if f.endswith(('.jpg', '.jpeg', '.png'))]
        
        for filename in files:
            name = os.path.splitext(filename)[0]
            path = os.path.join(FRUIT_ASSETS_DIR, filename)
            
            # Check if already exists
            stmt = select(Asset).where(Asset.path == path)
            result = await session.execute(stmt)
            existing_asset = result.scalar_one_or_none()
            
            if not existing_asset:
                print(f"Adding asset: {name} ({path})")
                new_asset = Asset(
                    name=name,
                    path=path,
                    asset_type="fruit"
                )
                session.add(new_asset)
            else:
                print(f"Asset already exists: {name}")
                
        await session.commit()
        print("Seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_fruits())
