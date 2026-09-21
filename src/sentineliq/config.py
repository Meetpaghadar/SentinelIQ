from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import tomli as tomllib
from pydantic import Field
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def _load_toml_defaults() -> dict[str, Any]:
    path = Path("config/settings.toml")
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    app = payload.get("app", {})
    defaults: dict[str, Any] = {}
    for key in ("env", "log_level", "host", "port"):
        if key in app:
            defaults[key] = app[key]
    return defaults


class TomlFileSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._data = _load_toml_defaults()

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        value = self._data.get(field_name)
        return value, field_name, False

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field_name, field in self.settings_cls.model_fields.items():
            value, key, is_complex = self.get_field_value(field, field_name)
            if value is not None:
                values[key] = self.prepare_field_value(field_name, field, value, is_complex)
        return values


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
    database_url: str | None = Field(
        default=None,
        validation_alias="SENTINELIQ_DATABASE_URL",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlFileSource(settings_cls),
            file_secret_settings,
        )

    def safe_display(self) -> dict[str, str | int]:
        return {
            "environment": self.env,
            "log_level": self.log_level,
            "host": self.host,
            "port": self.port,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


database_url: str = Field(
    validation_alias="SENTINELIQ_DATABASE_URL",
)
