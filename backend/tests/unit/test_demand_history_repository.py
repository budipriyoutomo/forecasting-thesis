"""CR v3.4 §4.2 — rentang periode demand (dasar perhitungan kelengkapan variabel eksternal)."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.repositories.demand_history_repository import SqlDemandHistoryRepository


def _session(row):
    s = MagicMock()
    result = MagicMock()
    result.one.return_value = row
    s.execute = AsyncMock(return_value=result)
    return s


@pytest.mark.asyncio
async def test_period_range_min_max():
    s = _session((date(2024, 1, 1), date(2025, 12, 1)))
    assert await SqlDemandHistoryRepository(s).period_range() == (date(2024, 1, 1), date(2025, 12, 1))
    sql = str(s.execute.await_args.args[0].compile(dialect=postgresql.dialect()))
    assert "min(demand_history.period)" in sql and "max(demand_history.period)" in sql


@pytest.mark.asyncio
async def test_period_range_kosong():
    s = _session((None, None))
    assert await SqlDemandHistoryRepository(s).period_range() == (None, None)


def _sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


@pytest.mark.asyncio
async def test_list_unnormalized_dan_normalized_keys():
    s = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["row"]
    result.all.return_value = [("u1", "A", date(2024, 1, 1))]
    s.execute = AsyncMock(return_value=result)
    s.flush = AsyncMock()
    repo = SqlDemandHistoryRepository(s)

    assert await repo.list_unnormalized() == ["row"]
    assert "EXTRACT(day FROM demand_history.period) !=" in _sql(s.execute.await_args.args[0])
    assert await repo.normalized_keys() == {("u1", "A", date(2024, 1, 1))}
    assert "EXTRACT(day FROM demand_history.period) =" in _sql(s.execute.await_args.args[0])
    await repo.flush()
    s.flush.assert_awaited_once()
