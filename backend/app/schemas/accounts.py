from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginStartRequest(BaseModel):
    label: str
    phone_number: str
    api_id: int
    api_hash: str


class LoginStartResponse(BaseModel):
    login_session_id: str


class VerifyCodeRequest(BaseModel):
    login_session_id: str
    code: str


class Verify2FARequest(BaseModel):
    login_session_id: str
    password: str


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    phone_number: str | None
    telegram_user_id: int | None
    username: str | None
    first_name: str | None
    last_name: str | None
    bio: str | None
    status: str
    status_detail: str | None
    created_at: datetime


class VerifyCodeResponse(BaseModel):
    status: str  # "needs_2fa" | "done"
    account: AccountOut | None = None
