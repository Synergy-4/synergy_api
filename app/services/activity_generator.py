import json
import logging
from typing import Optional, List
from google import genai

from app.core.config import settings
from app.models.child import Child
from app.models.goal import Goal
from app.models.session import Session
from app.schemas.activity import ActivityPayload

logger = logging.getLogger(__name__)

# Initialize GenAI Client
client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None

async def generate_activity(child: Child, goals: List[Goal], recent_sessions: List[Session]) -> ActivityPayload:
    if not client:
        raise ValueError("GEMINI_API_KEY is not configured")

    # Build context for Gemini
    child_context = {
        "name": child.name,
        "age_years": child.age_in_years,
        "interests": child.interests,
        "active_goals": [
            {"domain": g.domain, "description": g.description, "priority": g.priority}
            for g in goals
        ],
        "recent_game_types": []
    }
    
    for session in recent_sessions:
        if session.game_types:
            child_context["recent_game_types"].extend(session.game_types)
    child_context["recent_game_types"] = list(set(child_context["recent_game_types"][-5:]))

    system_prompt = """You are a specialist in autism therapy and child development.
Generate structured activity configurations for parents to use at home.
Activities must be evidence-based (ABA / naturalistic teaching),
5-10 minutes long, and appropriate for the child's age and goals.
Always vary game types from recent sessions. Never use clinical jargon
in parent-facing text — keep instructions warm, simple, and encouraging."""

    # Using the tool calling functionality to enforce JSON schema
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Generate a home activity for this child: {json.dumps(child_context)}",
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=ActivityPayload,
            )
        )
        
        # Parse the JSON response directly into the Pydantic model
        return ActivityPayload.model_validate_json(response.text)
    except Exception as e:
        logger.error(f"Error generating activity with Gemini: {e}")
        raise
