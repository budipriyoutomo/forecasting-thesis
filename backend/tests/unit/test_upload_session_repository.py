"""
Fase 3 — repositories upload/consumption dengan AsyncSession di-mock.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.upload_session_repository import (
    SqlConsumptionHistoryRepository,
    SqlUploadSessionRepository,
)


def _session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.get = AsyncMock()
    s.add = MagicMock()
    s.add_all = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_add_flush_refresh():
    session = _session()
    repo = SqlUploadSessionRepository(session)
    upload = object()

    result = await repo.add(upload)

    assert result is upload
    session.add.assert_called_once_with(upload)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(upload)


@pytest.mark.asyncio
async def test_get_by_id():
    session = _session()
    session.get.return_value = "sess"
    repo = SqlUploadSessionRepository(session)

    assert await repo.get_by_id("id-1") == "sess"


@pytest.mark.asyncio
async def test_list_by_user():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a", "b"]
    session.execute.return_value = result
    repo = SqlUploadSessionRepository(session)

    assert await repo.list_by_user("u1") == ["a", "b"]


@pytest.mark.asyncio
async def test_list_expired_pending():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["x"]
    session.execute.return_value = result
    repo = SqlUploadSessionRepository(session)

    got = await repo.list_expired_pending(datetime.now(timezone.utc))

    assert got == ["x"]


@pytest.mark.asyncio
async def test_save_flush():
    session = _session()
    repo = SqlUploadSessionRepository(session)
    upload = object()

    assert await repo.save(upload) is upload
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_consumption_bulk_add():
    session = _session()
    repo = SqlConsumptionHistoryRepository(session)
    rows = [object(), object()]

    count = await repo.bulk_add(rows)

    assert count == 2
    session.add_all.assert_called_once_with(rows)
    session.flush.assert_awaited_once()
