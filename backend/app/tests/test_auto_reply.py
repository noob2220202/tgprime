import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import AutoReplyLog, AutoReplyRule, TelegramAccount
from app.telegram import auto_reply
from app.telegram.crypto import encrypt


class FakeEvent:
    def __init__(self, chat_id: int, is_group: bool = False, is_channel: bool = False):
        self.chat_id = chat_id
        self.is_group = is_group
        self.is_channel = is_channel
        self.replies: list[str] = []

    async def reply(self, text: str) -> None:
        self.replies.append(text)


@pytest_asyncio.fixture
async def auto_reply_session_maker(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(auto_reply, "async_session_maker", session_maker)

    yield session_maker

    await engine.dispose()


async def _make_account(session_maker) -> str:
    async with session_maker() as db:
        account = TelegramAccount(
            label="Test", api_id=1, api_hash_encrypted=encrypt("h"), session_encrypted=encrypt("s"), status="active"
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return account.id


@pytest.mark.asyncio
async def test_no_rule_means_no_reply(auto_reply_session_maker):
    account_id = await _make_account(auto_reply_session_maker)
    event = FakeEvent(chat_id=555)

    await auto_reply._handle_incoming_message(account_id, event)

    assert event.replies == []


@pytest.mark.asyncio
async def test_disabled_rule_means_no_reply(auto_reply_session_maker):
    account_id = await _make_account(auto_reply_session_maker)
    async with auto_reply_session_maker() as db:
        db.add(AutoReplyRule(account_id=account_id, enabled=False, reply_text="hi", cooldown_minutes=60))
        await db.commit()

    event = FakeEvent(chat_id=555)
    await auto_reply._handle_incoming_message(account_id, event)

    assert event.replies == []


@pytest.mark.asyncio
async def test_enabled_rule_replies_once(auto_reply_session_maker):
    account_id = await _make_account(auto_reply_session_maker)
    async with auto_reply_session_maker() as db:
        db.add(AutoReplyRule(account_id=account_id, enabled=True, reply_text="hello!", cooldown_minutes=60))
        await db.commit()

    event = FakeEvent(chat_id=555)
    await auto_reply._handle_incoming_message(account_id, event)

    assert event.replies == ["hello!"]

    async with auto_reply_session_maker() as db:
        from sqlalchemy import select

        result = await db.execute(select(AutoReplyLog).where(AutoReplyLog.account_id == account_id))
        logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].peer_id == 555


@pytest.mark.asyncio
async def test_cooldown_prevents_duplicate_reply(auto_reply_session_maker):
    account_id = await _make_account(auto_reply_session_maker)
    async with auto_reply_session_maker() as db:
        db.add(AutoReplyRule(account_id=account_id, enabled=True, reply_text="hello!", cooldown_minutes=60))
        await db.commit()

    event1 = FakeEvent(chat_id=555)
    await auto_reply._handle_incoming_message(account_id, event1)
    assert event1.replies == ["hello!"]

    event2 = FakeEvent(chat_id=555)
    await auto_reply._handle_incoming_message(account_id, event2)
    assert event2.replies == []  # within cooldown, no second reply


@pytest.mark.asyncio
async def test_group_messages_are_ignored(auto_reply_session_maker):
    account_id = await _make_account(auto_reply_session_maker)
    async with auto_reply_session_maker() as db:
        db.add(AutoReplyRule(account_id=account_id, enabled=True, reply_text="hello!", cooldown_minutes=60))
        await db.commit()

    event = FakeEvent(chat_id=555, is_group=True)
    await auto_reply._handle_incoming_message(account_id, event)

    assert event.replies == []


def test_register_for_client_adds_handler():
    calls = []

    class FakeClient:
        def add_event_handler(self, handler, event):
            calls.append((handler, event))

    auto_reply.register_for_client("acc-1", FakeClient())
    assert len(calls) == 1
