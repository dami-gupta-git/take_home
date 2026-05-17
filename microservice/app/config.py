"""
Microservice settings loaded from environment variables and .env file.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    BATCH_SIZE: int = 1  # routes per callback; increase to reduce round-trips
    BATCH_DELAY_SECONDS: float = 0.5  # simulated processing latency between batches

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
