"""
Application settings loaded from environment variables and .env file.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Required — no defaults; service will fail fast on startup if missing
    DATABASE_URL: str
    MICROSERVICE_URL: str
    BACKEND_URL: str = "http://backend:8000"

    LOG_LEVEL: str = "INFO"

    # Pool tuning: defaults are conservative; increase for higher concurrency
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
