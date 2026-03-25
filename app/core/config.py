from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Synergy API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/synergy"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI Provider
    GEMINI_API_KEY: str = ""
    
    # Audio Storage
    AUDIO_STORAGE_BACKEND: str = "local"
    
    # Local backend
    AUDIO_LOCAL_DIR: str = "./audio_files"
    AUDIO_LOCAL_BASE_URL: str = "https://5304-154-160-19-166.ngrok-free.app"
    
    # R2 Storage
    R2_ENDPOINT_URL: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "synergy-audio"
    R2_PUBLIC_URL: str = ""

    ASSET_URL: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
