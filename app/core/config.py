from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "OmniHR Enterprise HRMS"
    API_V1_STR: str = "/api/v1"

    # Security & Tokens
    JWT_SECRET: str = "super-secret-omni-hr-key-change-in-production-32-bytes"
    JWT_REFRESH_SECRET: str = "super-secret-refresh-key-change-in-production-32-bytes"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day for dev, 15-60 min for prod
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/omni_hr"
    SQL_ECHO: bool = False

    # Redis Cache & PubSub
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=["backend/.env", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
