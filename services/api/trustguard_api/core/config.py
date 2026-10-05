# services/api/trustguard_api/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "TrustGuard API"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database & Cache
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:trustguard_dev_password@localhost:5432/trustguard",
        description="Async PostgreSQL connection URL"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and rate limiting"
    )

    # JWT Authentication
    JWT_SECRET_KEY: str = "dev-secret-key-please-change-in-production-at-least-32-chars-long"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Vishing Scoring Thresholds
    VISHING_CRITICAL_THRESHOLD: float = 75.0
    VISHING_CAUTION_THRESHOLD: float = 40.0

    # Deepfake Inference Service
    INFERENCE_GRPC_TARGET: str = "localhost:50051"

settings = Settings()
