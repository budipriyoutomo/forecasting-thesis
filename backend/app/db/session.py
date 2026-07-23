"""
Koneksi database (Supabase Postgres) — SQLAlchemy 2.0 async.

Engine dibuat **lazy** lewat `get_engine()`: import modul ini tidak membuka
koneksi apa pun, jadi test unit / health check tetap jalan tanpa DATABASE_URL
nyata. Backend tetap stateless (AGENTS.md §10 #10) — tidak ada state selain
connection pool.
"""
from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

ASYNC_DRIVER = "postgresql+asyncpg"


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    if not settings.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL belum di-set — salin backend/.env.example ke backend/.env "
            "dan isi koneksi Supabase Postgres."
        )

    # Supabase memberi URL berskema `postgresql://`; SQLAlchemy async butuh driver asyncpg.
    url = make_url(settings.DATABASE_URL)
    if not url.drivername.endswith("+asyncpg"):
        url = url.set(drivername=ASYNC_DRIVER)

    return create_async_engine(url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — satu session per request, selalu ditutup di akhir."""
    async with get_sessionmaker()() as session:
        yield session
