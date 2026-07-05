import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), default=DEFAULT_TENANT_ID, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), default=DEFAULT_TENANT_ID, index=True)

    label: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    api_id: Mapped[int] = mapped_column(Integer)
    api_hash_encrypted: Mapped[str] = mapped_column(Text)
    session_encrypted: Mapped[str] = mapped_column(Text)

    telegram_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="pending_login")
    status_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    flood_wait_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_profile_edit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LoginSession(Base):
    """Ephemeral interactive-login handshake state. Never stores OTP codes or 2FA passwords."""

    __tablename__ = "login_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), default=DEFAULT_TENANT_ID, index=True)

    label: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str] = mapped_column(String(32))
    api_id: Mapped[int] = mapped_column(Integer)
    api_hash: Mapped[str] = mapped_column(String(255))
    telethon_phone_code_hash: Mapped[str] = mapped_column(String(255))

    state: Mapped[str] = mapped_column(String(32), default="awaiting_code")
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BulkJob(Base):
    __tablename__ = "bulk_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), default=DEFAULT_TENANT_ID, index=True)

    job_type: Mapped[str] = mapped_column(String(64), default="bulk_profile_update")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    payload_template: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    total_items: Mapped[int] = mapped_column(Integer, default=0)
    succeeded_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BulkJobItem(Base):
    __tablename__ = "bulk_job_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("bulk_jobs.id"), index=True)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("telegram_accounts.id"), index=True)

    payload_override: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    flood_wait_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CachedDialog(Base):
    __tablename__ = "cached_dialogs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("telegram_accounts.id"), index=True)

    peer_id: Mapped[int] = mapped_column(Integer)
    peer_type: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255))
    photo_thumb_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutoReplyRule(Base):
    __tablename__ = "auto_reply_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("telegram_accounts.id"), unique=True, index=True)

    enabled: Mapped[bool] = mapped_column(default=False)
    reply_text: Mapped[str] = mapped_column(Text, default="")
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=60)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutoReplyLog(Base):
    __tablename__ = "auto_reply_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("telegram_accounts.id"), index=True)
    peer_id: Mapped[int] = mapped_column(Integer, index=True)
    replied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
