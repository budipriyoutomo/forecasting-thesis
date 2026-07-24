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
