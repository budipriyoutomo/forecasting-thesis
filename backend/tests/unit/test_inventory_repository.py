"""Fase 11.5 — repository stok ERP (AsyncSession di-mock)."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.inventory import StockSnapshot
from app.repositories.inventory_repository import SqlStockSnapshotRepository


def _session():
    s = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["x"]
    s.execute = AsyncMock(return_value=result)
    s.get = AsyncMock(return_value="x")
    s.add, s.add_all = MagicMock(), MagicMock()
    s.flush, s.refresh, s.delete = AsyncMock(), AsyncMock(), AsyncMock()
    return s


@pytest.mark.asyncio
async def test_snapshot_repo():
    s = _session()
    repo = SqlStockSnapshotRepository(s)
    rows = [StockSnapshot(material_id="m1", snapshot_date=date(2026, 1, 1), qty=1)]
    assert await repo.upsert(rows) == 1
    assert await repo.list("m1", date(2026, 1, 1)) == ["x"]
