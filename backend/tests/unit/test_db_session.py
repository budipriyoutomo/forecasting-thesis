"""
Fase 0 — koneksi database (Supabase Postgres) via SQLAlchemy 2.0 async.

Engine dibuat lazy: import modul ini TIDAK boleh membuka koneksi, supaya test
unit & health check tetap jalan tanpa DATABASE_URL nyata.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import session as db_session


@pytest.fixture(autouse=True)
def reset_engine_cache():
    db_session.get_engine.cache_clear()
    db_session.get_sessionmaker.cache_clear()
    yield
    db_session.get_engine.cache_clear()
    db_session.get_sessionmaker.cache_clear()


def test_get_engine_pakai_database_url_dari_settings(monkeypatch):
    monkeypatch.setattr(
        db_session.get_settings(), "DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/forecastiq"
    )

    engine = db_session.get_engine()

    assert isinstance(engine, AsyncEngine)
    assert engine.url.database == "forecastiq"


def test_get_engine_error_jelas_kalau_database_url_kosong(monkeypatch):
    monkeypatch.setattr(db_session.get_settings(), "DATABASE_URL", None)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db_session.get_engine()


def test_get_engine_dicache_tidak_bikin_engine_baru_tiap_panggilan(monkeypatch):
    monkeypatch.setattr(
        db_session.get_settings(), "DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/forecastiq"
    )

    assert db_session.get_engine() is db_session.get_engine()


def test_driver_async_dipaksa_walau_url_pakai_skema_sync(monkeypatch):
    """Supabase memberi URL `postgresql://...`; SQLAlchemy async butuh driver asyncpg."""
    monkeypatch.setattr(db_session.get_settings(), "DATABASE_URL", "postgresql://u:p@localhost:5432/forecastiq")

    engine = db_session.get_engine()

    assert engine.url.drivername == "postgresql+asyncpg"


@pytest.mark.asyncio
async def test_get_db_menghasilkan_async_session(monkeypatch):
    monkeypatch.setattr(
        db_session.get_settings(), "DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/forecastiq"
    )

    agen = db_session.get_db()
    sess = await agen.__anext__()
    try:
        assert sess.bind is db_session.get_engine()
    finally:
        await agen.aclose()
