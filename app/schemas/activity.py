from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

# -------------------------------------------------------------
# Core SDUI Payload Components (Mirroring Flutter/Dart Models)
# -------------------------------------------------------------

class FontConfig(BaseModel):
    family: str
    size: float
    weight: str
    color: str

class ThemeConfig(BaseModel):
    primary_color: str
    secondary_color: str
    background_color: str
    card_color: str
    success_color: Optional[str] = "#4CAF50"
    error_color: Optional[str] = "#F44336"
    heading_font: FontConfig
    body_font: FontConfig

class GameConfig(BaseModel):
    game_type: str # "matching", "sorting", "tracing"
    difficulty: str # "easy", "medium", "hard"
    time_limit_seconds: Optional[int] = None
    parent_instruction: Optional[str] = None
    parent_instruction_audio_url: Optional[str] = None
    data: Dict[str, Any] # Game-specific configuration, e.g., pairs for matching

class StepConfig(BaseModel):
    id: str
    type: str # "instruction", "game", "reward"
    title: str
    description: Optional[str] = None
    voiceover_text: Optional[str] = None
    voiceover_audio_url: Optional[str] = None
    game_config: Optional[GameConfig] = None
    lottie_url: Optional[str] = None # For reward steps

class ActivityPayload(BaseModel):
    version: str = "1.0.0"
    activity_id: Optional[int] = None
    theme: ThemeConfig
    steps: List[StepConfig]

# -------------------------------------------------------------
# REST API Request/Response Schemas
# -------------------------------------------------------------

class ActivityBase(BaseModel):
    ai_generated: bool
    theme_id: str
    game_types: List[str]
    ui_config: ActivityPayload

class ActivityCreate(ActivityBase):
    child_id: int

class ActivityUpdate(BaseModel):
    pass

class ActivityInDBBase(ActivityBase):
    id: int
    child_id: int

    class Config:
        from_attributes = True

class Activity(ActivityInDBBase):
    pass
