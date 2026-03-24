import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import text

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
from app.models.asset import Asset
from app.schemas.activity import ActivityPayload, ThemeConfig, FontConfig, GameConfig, StepConfig
from app.services.activity_generator import generate_activity
from app.services.activity_validator import validate_and_fallback, get_fallback_activity

import random

router = APIRouter()

@router.get("/next/{child_id}", response_model=ActivityPayload)
@limiter.limit("12/minute")
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
        
    cache_key = f"activity:next:{child_id}:{game_type}"
    
    # 1. Check Redis Cache
    cached_payload = await redis_client.get(cache_key)
    if cached_payload:
        try:
            payload_dict = json.loads(cached_payload)
            return ActivityPayload(**payload_dict)
        except Exception:
            pass # Fall through to generate
            
    # 2. Load context (goals, recent sessions)
    stmt = text("select * from sessions join activities on sessions.activity_id = activities.id where sessions.child_id = :child_id order by sessions.created_at desc limit 5")
    recent_sessions_result = await db.execute(stmt, {"child_id": child_id})

    recent_sessions = recent_sessions_result.all()
    
    # 3. Load available assets for AI context
    assets_result = await db.execute(select(Asset))
    assets = assets_result.scalars().all()
    random.shuffle(assets)
    
    # 4. Generate AI Activity
    try:
        activity_payload = await generate_activity(
            child=child, 
            goals=child.goals, 
            recent_sessions=recent_sessions,
            assets=assets,
            game_type=game_type
        )
    except Exception as e:
        print(e)
        app.logger.error("Activity generation failed, using fallback")
        activity_payload = get_fallback_activity()
        
    validated_payload = validate_and_fallback(activity_payload.model_dump())

    # 5. Inject audio URLs — all TTS generation happens here
    from app.services.audio_injection_service import inject_audio_urls
    payload_dict = await inject_audio_urls(validated_payload.model_dump())

    # 6. Cache and Store
    await redis_client.setex(
        cache_key,
        14400, # Cache for 4 hours
        json.dumps(payload_dict)
    )
    
    game_types = list({
        step.get("game_config", {}).get("game_type")
        for step in payload_dict.get("steps", [])
        if step.get("game_config") and step.get("game_config").get("game_type")
    })
    
    db_activity = Activity(
        child_id=child_id,
        ui_config=payload_dict,
        ai_generated=True,
        theme_id="dynamic_ai",
        game_types=game_types
    )
    db.add(db_activity)
    await db.commit()
    
    await db.refresh(db_activity)
    payload_dict["activity_id"] = db_activity.id

    return ActivityPayload(**payload_dict)
