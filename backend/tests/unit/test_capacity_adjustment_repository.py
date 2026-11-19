"""Fase 11.17 — SqlCapacityAdjustmentRepository dengan AsyncSession di-mock (append-only)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.capacity_adjustment_repository import SqlCapacityAdjustmentRepository


def _session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.add_all = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_add_all_append_only():
    session = _session()
    rows = [object(), object()]
    assert await SqlCapacityAdjustmentRepository(session).add_all(rows) == rows
    session.add_all.assert_called_once_with(rows)
    session.flush.assert_awaited_once()
    assert session.refresh.await_count == 2


@pytest.mark.asyncio
async def test_list_by_run():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a"]
    session.execute.return_value = result
    assert await SqlCapacityAdjustmentRepository(session).list_by_run("r1") == ["a"]
    session.execute.assert_awaited_once()
