from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.auth.csrf import RequireRequestedWithMiddleware
from app.auth.security import hash_password
from app.config import get_settings
from app.db.base import async_session_maker
from app.db.models import User
from app.jobs.queue import recover_pending_items, start_workers, stop_workers
from app.routers import accounts as accounts_router
from app.routers import auth as auth_router
from app.routers import auto_reply as auto_reply_router
from app.routers import bulk_jobs as bulk_jobs_router
from app.routers import chat as chat_router
from app.routers import stories as stories_router
from app.telegram import auto_reply, background_tasks
from app.telegram.client_pool import pool


async def _seed_admin_user() -> None:
    settings = get_settings()
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.username == settings.admin_username))
        if result.scalar_one_or_none() is not None:
            return
        db.add(User(username=settings.admin_username, password_hash=hash_password(settings.admin_password)))
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed by Alembic migrations (run `alembic upgrade head` before first start).
    await _seed_admin_user()
    pool.on_new_client(auto_reply.register_for_client)
    settings = get_settings()
    start_workers(settings.bulk_job_worker_count)
    await recover_pending_items()
    background_tasks.start(settings.health_check_interval_seconds, settings.idle_client_timeout_minutes)
    yield
    await background_tasks.stop()
    await stop_workers()
    await pool.disconnect_all()


app = FastAPI(title="Telegram Prime", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequireRequestedWithMiddleware)

app.include_router(auth_router.router)
app.include_router(accounts_router.router)
app.include_router(chat_router.router)
app.include_router(chat_router.ws_router)
app.include_router(bulk_jobs_router.router)
app.include_router(auto_reply_router.router)
app.include_router(stories_router.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
