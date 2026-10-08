Exit code: 0
Wall time: 0.7 seconds
Output:
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", enable_decoding=False)

    bot_token: str = Field(alias="BOT_TOKEN")
    api_id: int = Field(alias="API_ID")
    api_hash: str = Field(alias="API_HASH")
    mongo_uri: str = Field(alias="MONGO_URI")
    mongo_db: str = Field(default="televault", alias="MONGO_DB")
    admins: list[int] = Field(default_factory=list, alias="ADMINS")
    log_channel_id: int | None = Field(default=None, alias="LOG_CHANNEL_ID")
    force_sub_channels: list[int] = Field(default_factory=list, alias="FORCE_SUB_CHANNELS")
    source_channels: list[int] = Field(default_factory=list, alias="SOURCE_CHANNELS")
    free_daily_file_limit: int = Field(default=5, ge=1, le=100, alias="FREE_DAILY_FILE_LIMIT")
    referral_reward_days: int = Field(default=7, ge=1, le=365, alias="REFERRAL_REWARD_DAYS")

    @field_validator("admins", "force_sub_channels", "source_channels", mode="before")
    @classmethod
    def parse_id_list(cls, value: object) -> list[int]:
        if value in (None, ""):
            return []
        if isinstance(value, str):
            return [int(item) for item in value.replace(",", " ").split()]
        return [int(item) for item in value]  # type: ignore[arg-type]


@lru_cache
def get_settings() -> Settings:
    return Settings()

