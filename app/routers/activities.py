import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.redis import get_redis_client
from app.core.rate_limit import limiter
import redis.asyncio as redis
from app.models.user import User
from app.models.child import Child
from app.models.activity import Activity
from app.models.goal import Goal
from app.models.session import Session
from app.schemas.activity import ActivityPayload, ThemeConfig, FontConfig, GameConfig, StepConfig
from app.services.activity_generator import generate_activity
from app.services.activity_validator import validate_and_fallback, get_fallback_activity

router = APIRouter()

@router.get("/next/{child_id}", response_model=ActivityPayload)
@limiter.limit("5/minute")
async def get_next_activity(
    request: Request,
    child_id: int,
    game_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    # Verify child exists and belongs to user
    result = await db.execute(
        select(Child)
        .options(selectinload(Child.goals))
        .filter(Child.id == child_id, Child.parent_id == current_user.id)
    )
    child = result.scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
        
    cache_key = f"activity:next:{child_id}"
    
    # 1. Check Redis Cache
    cached_payload = await redis_client.get(cache_key)
    if cached_payload:
        try:
            payload_dict = json.loads(cached_payload)
            return validate_and_fallback(payload_dict)
        except Exception:
            pass # Fall through to generate
            
    # 2. Load context (goals, recent sessions)
    recent_sessions_result = await db.execute(
        select(Session)
        .filter(Session.child_id == child_id)
        .order_by(Session.created_at.desc())
        .limit(5)
    )
    recent_sessions = recent_sessions_result.scalars().all()
    
    # 3. Generate AI Activity
    try:
        activity_payload = await generate_activity(
            child=child, 
            goals=child.goals, 
            recent_sessions=recent_sessions,
            game_type=game_type
        )
    except Exception as e:
        print(e)
        # Fallback to static template on API failure
        # In a real app we might still cache this temporarily to prevent hammering the failing API
        activity_payload = get_fallback_activity()
        
    # Validation step to ensure the returned tool_use payload matches the API schema
    # Pydantic is already applied inside `generate_activity` structurally, but this serves as a final check
    # if we wanted to allow modifications
    validated_payload = validate_and_fallback(activity_payload.model_dump())

    # 4. Cache and Store
    await redis_client.setex(
        cache_key,
        14400, # Cache for 4 hours
        json.dumps(validated_payload.model_dump())
    )
    
    db_activity = Activity(
        child_id=child_id,
        ui_config=validated_payload.model_dump(),
        ai_generated=True,
        theme_id="dynamic_ai",
        game_types=[] # we could extract game types from the payload steps
    )
    db.add(db_activity)
    await db.commit()
    
    return validated_payload
