from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    admin_username: str = "admin"
    admin_password: str = "change-me"

    session_secret: str = "change-me-too"
    master_encryption_key: str = ""

    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    bulk_job_worker_count: int = 3

    telegram_login_min_delay_seconds: float = 1.0
    telegram_login_max_delay_seconds: float = 2.0

    profile_edit_min_jitter_seconds: float = 3.0
    profile_edit_max_jitter_seconds: float = 15.0
    profile_edit_min_cooldown_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
