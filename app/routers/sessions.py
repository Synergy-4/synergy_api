from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.child import Child
from app.models.session import Session
from app.schemas.session import SessionCreate, Session as SessionSchema

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_session(
    session_in: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify child belongs to parent
    result = await db.execute(select(Child).filter(Child.id == session_in.child_id, Child.parent_id == current_user.id))
    child = result.scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
        
    session = Session(**session_in.model_dump())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

@router.get("/{child_id}/history")
async def get_session_history(
    child_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify child belongs to parent
    result = await db.execute(select(Child).filter(Child.id == child_id, Child.parent_id == current_user.id))
    child = result.scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
        
    result = await db.execute(
        select(Session)
        .filter(Session.child_id == child_id)
        .order_by(Session.created_at.desc())
        .offset(skip).limit(limit)
    )
    return result.scalars().all()
