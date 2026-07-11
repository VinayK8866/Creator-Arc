from typing import Any, Dict, Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CreatorArc"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super-secret-jwt-signing-key-change-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "creator_arc"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def assemble_db_connection(cls, data: Any) -> Any:
        if isinstance(data, dict):
            db_uri = data.get("SQLALCHEMY_DATABASE_URI")
            if not db_uri:
                user = data.get("POSTGRES_USER", "postgres")
                password = data.get("POSTGRES_PASSWORD", "postgres")
                server = data.get("POSTGRES_SERVER", "localhost")
                db = data.get("POSTGRES_DB", "creator_arc")
                data["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{user}:{password}@{server}/{db}"
        return data

    # Redis Broker & Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_CELERY: bool = False

    # Security Configuration
    MASTER_PASSWORD: str = "creatorarc-dev-secret-pass"

    # External APIs
    GEMINI_API_KEY: Optional[str] = None

    # S3 Compatible Object Storage
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
