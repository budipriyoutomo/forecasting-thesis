"""
Fase 1 — SqlUserRepository dengan AsyncSession di-mock (tanpa DB nyata).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.user_repository import SqlUserRepository


@pytest.mark.asyncio
async def test_get_by_email_mengembalikan_user():
    sentinel = object()
    result = MagicMock()
    result.scalar_one_or_none.return_value = sentinel
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    repo = SqlUserRepository(session)
    user = await repo.get_by_email("a@b.com")

    assert user is sentinel
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_email_tidak_ada_none():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    repo = SqlUserRepository(session)

    assert await repo.get_by_email("ghost@b.com") is None


@pytest.mark.asyncio
async def test_get_by_id_delegasi_ke_session_get():
    sentinel = object()
    session = MagicMock()
    session.get = AsyncMock(return_value=sentinel)

    repo = SqlUserRepository(session)
    user = await repo.get_by_id("some-uuid")

    assert user is sentinel
    session.get.assert_awaited_once()


# ── CR v3.7 — User Management ──

@pytest.mark.asyncio
async def test_get_by_email_tidak_peka_huruf_besar():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    await SqlUserRepository(session).get_by_email("Budi@Corp.com")

    sql = str(session.execute.await_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "lower(users.email)" in sql
    assert "'budi@corp.com'" in sql


@pytest.mark.asyncio
async def test_list_urut_email():
    users = [object(), object()]
    result = MagicMock()
    result.scalars.return_value.all.return_value = users
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)

    assert await SqlUserRepository(session).list() == users
    sql = str(session.execute.await_args.args[0])
    assert "ORDER BY users.email" in sql


@pytest.mark.asyncio
async def test_save_flush_dan_refresh():
    user = object()
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    assert await SqlUserRepository(session).save(user) is user
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_create_add_flush_refresh_dan_default_aktif():
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    user = await SqlUserRepository(session).create(email="a@b.com", name="A", role="viewer", is_verified=True)

    session.add.assert_called_once_with(user)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)
    assert (user.email, user.role, user.is_verified) == ("a@b.com", "viewer", True)
