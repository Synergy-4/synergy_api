from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.child import Child
from app.models.goal import Goal
from app.schemas.child import ChildCreate, Child as ChildSchema, ChildUpdate
from app.schemas.goal import GoalCreate

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_child(
    child_in: ChildCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    child = Child(
        **child_in.model_dump(),
        parent_id=current_user.id
    )
    db.add(child)
    await db.commit()
    await db.refresh(child)
    return child

@router.get("/", response_model=List[ChildSchema])
async def read_children(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Child)
        .options(selectinload(Child.goals))
        .filter(Child.parent_id == current_user.id, Child.is_deleted == False)
        .offset(skip).limit(limit)
    )
    children = result.scalars().all()
    # Manual filter for goals since selectinload filter can be tricky with some versions
    for child in children:
        child.goals = [g for g in child.goals if not g.is_deleted]
    return children

@router.get("/{child_id}", response_model=ChildSchema)
async def read_child(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Child)
        .options(selectinload(Child.goals))
        .filter(Child.id == child_id, Child.parent_id == current_user.id, Child.is_deleted == False)
    )
    child = result.scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    child.goals = [g for g in child.goals if not g.is_deleted]
    return child

@router.post("/{child_id}/goals", response_model=ChildSchema)
async def add_child_goal(
    child_id: int,
    goal_in: GoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify child belongs to parent and is not deleted
    result = await db.execute(
        select(Child).filter(Child.id == child_id, Child.parent_id == current_user.id, Child.is_deleted == False)
    )
    child = result.scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
        
    goal = Goal(**goal_in.model_dump(), child_id=child.id)
    db.add(goal)
    await db.commit()
    
    # Refresh child to include new goal
    result = await db.execute(
        select(Child).options(selectinload(Child.goals)).filter(Child.id == child_id)
    )
    child = result.scalars().first()
    if child:
        child.goals = [g for g in child.goals if not g.is_deleted]
    return child

@router.patch("/{child_id}", response_model=ChildSchema)
async def update_child(
    child_id: int,
    child_in: ChildUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Child).filter(Child.id == child_id, Child.parent_id == current_user.id, Child.is_deleted == False)
    )
    child = result.scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
        
    update_data = child_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(child, field, value)
        
    await db.commit()
    await db.refresh(child)
    
    # Reload with goals
    result = await db.execute(
        select(Child).options(selectinload(Child.goals)).filter(Child.id == child_id)
    )
    child = result.scalars().first()
    child.goals = [g for g in child.goals if not g.is_deleted]
    return child

@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Child).filter(Child.id == child_id, Child.parent_id == current_user.id, Child.is_deleted == False)
    )
    child = result.scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
        
    child.is_deleted = True
    # Also soft delete goals? Usually yes.
    result = await db.execute(
        select(Goal).filter(Goal.child_id == child_id)
    )
    goals = result.scalars().all()
    for goal in goals:
        goal.is_deleted = True
        
    await db.commit()
    return None

@router.delete("/{child_id}/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child_goal(
    child_id: int,
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify child belongs to parent and is not deleted
    result = await db.execute(
        select(Child).filter(Child.id == child_id, Child.parent_id == current_user.id, Child.is_deleted == False)
    )
    child = result.scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
        
    result = await db.execute(
        select(Goal).filter(Goal.id == goal_id, Goal.child_id == child_id, Goal.is_deleted == False)
    )
    goal = result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    goal.is_deleted = True
    await db.commit()
    return None
