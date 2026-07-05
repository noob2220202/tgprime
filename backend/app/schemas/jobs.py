from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BulkJobCreate(BaseModel):
    account_ids: list[str]
    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    username: str | None = None
    per_account: dict[str, dict] | None = None  # account_id -> field overrides


class BulkJobItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    status: str
    attempt_count: int
    error_message: str | None
    flood_wait_seconds: int | None
    started_at: datetime | None
    finished_at: datetime | None


class BulkJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_type: str
    status: str
    total_items: int
    succeeded_count: int
    failed_count: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class BulkJobDetailOut(BulkJobOut):
    items: list[BulkJobItemOut]
