from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    env: str = Field(default="development", validation_alias="SENTINELIQ_ENV")
    log_level: str = Field(default="INFO", validation_alias="SENTINELIQ_LOG_LEVEL")
    host: str = Field(default="0.0.0.0", validation_alias="SENTINELIQ_HOST")
    port: int = Field(default=8000, validation_alias="SENTINELIQ_PORT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
