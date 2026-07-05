from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.db.models import AutoReplyRule, TelegramAccount
from app.schemas.auto_reply import AutoReplyRuleOut, AutoReplyRuleUpdate

router = APIRouter(prefix="/api/accounts", tags=["auto-reply"], dependencies=[Depends(get_current_user)])


async def _get_or_create_rule(db: AsyncSession, account_id: str) -> AutoReplyRule:
    result = await db.execute(select(AutoReplyRule).where(AutoReplyRule.account_id == account_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        rule = AutoReplyRule(account_id=account_id, enabled=False, reply_text="", cooldown_minutes=60)
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
    return rule


@router.get("/{account_id}/auto-reply", response_model=AutoReplyRuleOut)
async def get_auto_reply(account_id: str, db: AsyncSession = Depends(get_db)):
    account = await db.get(TelegramAccount, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    return await _get_or_create_rule(db, account_id)


@router.put("/{account_id}/auto-reply", response_model=AutoReplyRuleOut)
async def update_auto_reply(account_id: str, payload: AutoReplyRuleUpdate, db: AsyncSession = Depends(get_db)):
    account = await db.get(TelegramAccount, account_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")

    rule = await _get_or_create_rule(db, account_id)
    rule.enabled = payload.enabled
    rule.reply_text = payload.reply_text
    rule.cooldown_minutes = payload.cooldown_minutes
    await db.commit()
    await db.refresh(rule)
    return rule
