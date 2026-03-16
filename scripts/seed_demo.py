import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal, Base, engine
from app.models.user import User
from app.models.child import Child
from app.models.goal import Goal
from app.core.security import get_password_hash

async def seed_data():
    async with AsyncSessionLocal() as db:
        # 1. Create a demo user
        demo_user = User(
            email="parent@example.com",
            hashed_password=get_password_hash("password123"),
            role="parent",
            is_active=True
        )
        db.add(demo_user)
        await db.flush() # Get user ID
        
        # 2. Create kids
        child1 = Child(
            parent_id=demo_user.id,
            name="Leo",
            age_in_years=5,
            interests=["blocks", "trains", "music"],
            diagnosis_notes="Level 1 ASD, slight speech delay"
        )
        child2 = Child(
            parent_id=demo_user.id,
            name="Mia",
            age_in_years=7,
            interests=["dinosaurs", "drawing", "puzzles"],
            diagnosis_notes="ADHD, sensory processing differences"
        )
        db.add_all([child1, child2])
        await db.flush()
        
        # 3. Create goals for Leo
        goals_leo = [
            Goal(child_id=child1.id, domain="Communication", description="Ask for help using 2-3 words", priority=1),
            Goal(child_id=child1.id, domain="Social Skills", description="Turn taking during block play", priority=2)
        ]
        
        # 4. Create goals for Mia
        goals_mia = [
            Goal(child_id=child2.id, domain="Motor Skills", description="Pincer grasp for drawing", priority=1),
            Goal(child_id=child2.id, domain="Communication", description="Identify emotions in others", priority=2)
        ]
        
        db.add_all(goals_leo + goals_mia)
        
        await db.commit()
        print("Demo data seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
