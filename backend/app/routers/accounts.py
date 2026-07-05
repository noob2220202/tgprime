from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    RPCError,
)

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import TelegramAccount
from app.schemas.accounts import (
    AccountOut,
    LoginStartRequest,
    LoginStartResponse,
    Verify2FARequest,
    VerifyCodeRequest,
    VerifyCodeResponse,
)
from app.telegram import login_flow, session_import
from app.telegram.health_check import check_account_health
from app.telegram.login_flow import LoginSessionExpired
from app.telegram.session_import import SessionNotAuthorized

MAX_SESSION_FILE_BYTES = 5 * 1024 * 1024

router = APIRouter(prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AccountOut])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TelegramAccount).order_by(TelegramAccount.created_at))
    return list(result.scalars().all())


@router.post("/login/start", response_model=LoginStartResponse)
async def login_start(payload: LoginStartRequest, db: AsyncSession = Depends(get_db)):
    try:
        login_session = await login_flow.start_login(
            db, payload.label, payload.phone_number, payload.api_id, payload.api_hash
        )
    except PhoneNumberInvalidError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "유효하지 않은 전화번호입니다.")
    except RPCError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return LoginStartResponse(login_session_id=login_session.id)


@router.post("/login/verify-code", response_model=VerifyCodeResponse)
async def login_verify_code(payload: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    try:
        result_status, account = await login_flow.verify_code(db, payload.login_session_id, payload.code)
    except PhoneCodeInvalidError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "인증 코드가 올바르지 않습니다.")
    except PhoneCodeExpiredError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "인증 코드가 만료됐습니다. 처음부터 다시 시도해주세요.")
    except LoginSessionExpired as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return VerifyCodeResponse(status=result_status, account=account)


@router.post("/login/verify-2fa", response_model=AccountOut)
async def login_verify_2fa(payload: Verify2FARequest, db: AsyncSession = Depends(get_db)):
    try:
        account = await login_flow.verify_2fa(db, payload.login_session_id, payload.password)
    except PasswordHashInvalidError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "2단계 인증 비밀번호가 올바르지 않습니다.")
    except LoginSessionExpired as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return account


@router.post("/import-session", response_model=AccountOut)
async def import_session(
    label: str = Form(...),
    api_id: int = Form(...),
    api_hash: str = Form(...),
    session_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await session_file.read()
    if len(file_bytes) > MAX_SESSION_FILE_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "파일이 너무 큽니다.")

    try:
        account = await session_import.import_session_file(db, label, api_id, api_hash, file_bytes)
    except SessionNotAuthorized as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except RPCError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return account


@router.post("/{account_id}/refresh-status", response_model=AccountOut)
async def refresh_account_status(account_id: str, db: AsyncSession = Depends(get_db)):
    account = await db.get(TelegramAccount, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    await check_account_health(db, account)
    await db.commit()
    await db.refresh(account)
    return account
