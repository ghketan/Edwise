import os
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_INSECURE_SECRET = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"


class Settings(BaseSettings):
    PROJECT_NAME: str = "EDWISE Learning Analytics Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./edwise.db"
    
    # Security & JWT
    SECRET_KEY: str = DEFAULT_INSECURE_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]

    # File paths
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    MODEL_ARTIFACTS_DIR: str = os.path.join(BASE_DIR, "app", "ml_engine", "artifacts")
    EXPORT_DIR: str = os.path.join(BASE_DIR, "exports")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        # Check against default insecure key in production (C-08)
        env = os.environ.get("ENVIRONMENT", "development")
        if env.lower() == "production" and (not v or v == DEFAULT_INSECURE_SECRET):
            raise ValueError("SECRET_KEY must be configured with a secure random key in production!")
        return v


settings = Settings()
os.makedirs(settings.MODEL_ARTIFACTS_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True)
