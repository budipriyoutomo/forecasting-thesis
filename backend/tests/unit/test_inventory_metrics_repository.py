"""Fase 7 — SqlInventoryMetricsRepository dengan AsyncSession di-mock."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.inventory_metrics_repository import SqlInventoryMetricsRepository


def _session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_replace_for_run_hapus_lalu_tambah():
    session = _session()
    repo = SqlInventoryMetricsRepository(session)
    rows = [object(), object()]

    out = await repo.replace_for_run("r1", rows)

    assert out is rows
    session.execute.assert_awaited_once()  # DELETE lama
    assert session.add.call_count == 2
    session.flush.assert_awaited_once()
    assert session.refresh.await_count == 2


@pytest.mark.asyncio
async def test_replace_for_run_kosong():
    session = _session()
    repo = SqlInventoryMetricsRepository(session)

    out = await repo.replace_for_run("r1", [])

    assert out == []
    session.add.assert_not_called()
    session.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_by_run():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a", "b"]
    session.execute.return_value = result
    repo = SqlInventoryMetricsRepository(session)

    assert await repo.list_by_run("r1") == ["a", "b"]
