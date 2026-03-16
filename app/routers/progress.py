from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.child import Child
from app.models.session import Session

router = APIRouter()

@router.get("/{child_id}/progress")
async def get_child_progress(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify child belongs to parent
    result = await db.execute(select(Child).filter(Child.id == child_id, Child.parent_id == current_user.id))
    child = result.scalars().first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
        
    # Calculate some basic aggregate statistics from all sessions for this child
    sessions_result = await db.execute(
        select(Session)
        .filter(Session.child_id == child_id)
    )
    sessions = sessions_result.scalars().all()
    
    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s.completed)
    total_duration_minutes = sum(s.duration_seconds for s in sessions if s.duration_seconds) / 60 if sessions else 0
    
    # Aggregate scores roughly across game types (domain breakdown)
    domain_scores: Dict[str, List[int]] = {}
    for session in sessions:
        if session.scores:
            for game_type, score in session.scores.items():
                if game_type not in domain_scores:
                    domain_scores[game_type] = []
                domain_scores[game_type].append(score)
                
    average_scores = {
        domain: sum(scores) / len(scores) for domain, scores in domain_scores.items()
    }
    
    return {
        "child_id": child_id,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "total_duration_minutes": round(total_duration_minutes, 1),
        "average_game_scores": average_scores,
    }
