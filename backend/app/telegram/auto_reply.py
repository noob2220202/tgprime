from datetime import datetime, timedelta

from sqlalchemy import select
from telethon import TelegramClient, events

from app.db.base import async_session_maker
from app.db.models import AutoReplyLog, AutoReplyRule


async def _handle_incoming_message(account_id: str, event: events.NewMessage.Event) -> None:
    if event.is_group or event.is_channel:
        return  # MVP: 1:1 auto-reply only, not group/channel auto-response

    peer_id = event.chat_id

    async with async_session_maker() as db:
        result = await db.execute(select(AutoReplyRule).where(AutoReplyRule.account_id == account_id))
        rule = result.scalar_one_or_none()
        if rule is None or not rule.enabled or not rule.reply_text:
            return

        cutoff = datetime.utcnow() - timedelta(minutes=rule.cooldown_minutes)
        result = await db.execute(
            select(AutoReplyLog).where(
                AutoReplyLog.account_id == account_id,
                AutoReplyLog.peer_id == peer_id,
                AutoReplyLog.replied_at > cutoff,
            )
        )
        if result.scalar_one_or_none() is not None:
            return  # already auto-replied to this peer recently

        reply_text = rule.reply_text

    await event.reply(reply_text)

    async with async_session_maker() as db:
        db.add(AutoReplyLog(account_id=account_id, peer_id=peer_id))
        await db.commit()


def register_for_client(account_id: str, client: TelegramClient) -> None:
    async def handler(event: events.NewMessage.Event) -> None:
        await _handle_incoming_message(account_id, event)

    client.add_event_handler(handler, events.NewMessage(incoming=True))
