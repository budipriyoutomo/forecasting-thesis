"""
Fase 6 — SqlOverrideRepository dengan AsyncSession di-mock (append-only).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.override_repository import SqlOverrideRepository


def _session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_add_append_only():
    session = _session()
    repo = SqlOverrideRepository(session)
    ov = object()

    assert await repo.add(ov) is ov
    session.add.assert_called_once_with(ov)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(ov)


@pytest.mark.asyncio
async def test_list_by_target():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a", "b"]
    session.execute.return_value = result
    repo = SqlOverrideRepository(session)

    assert await repo.list_by_target("t1") == ["a", "b"]
