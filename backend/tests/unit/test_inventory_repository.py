"""Fase 11.5 — repository stok ERP & kedatangan (AsyncSession di-mock)."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.inventory import MaterialReceipt, StockSnapshot
from app.repositories.inventory_repository import SqlMaterialReceiptRepository, SqlStockSnapshotRepository


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


@pytest.mark.asyncio
async def test_receipt_repo():
    s = _session()
    repo = SqlMaterialReceiptRepository(s)
    assert await repo.list("m1", date(2026, 1, 1), date(2026, 2, 1)) == ["x"]
    assert await repo.get_by_id("r1") == "x"
    row = MaterialReceipt(material_id="m1", expected_date=date(2026, 1, 1), qty=1)
    assert await repo.add(row) is row
    assert await repo.add_all([row]) == 1
    assert await repo.save(row) is row
    await repo.delete(row)
