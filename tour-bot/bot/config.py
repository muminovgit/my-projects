from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing import Annotated


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    admin_ids: Annotated[list[int], NoDecode] = []
    # Telegram group for leads and bookings; can also be set from the group with /setgroup
    admin_group_id: int | None = None
    database_url: str = "sqlite+aiosqlite:///tour_bot.db"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5-5"

    @field_validator("admin_ids", mode="before")
    @classmethod
    def split_ids(cls, value):
        if isinstance(value, str):
            return [int(part) for part in value.replace(" ", "").split(",") if part]
        return value
