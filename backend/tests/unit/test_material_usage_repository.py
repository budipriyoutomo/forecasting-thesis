"""Fase 11.1 — SqlMaterialUsageRepository (AsyncSession di-mock)."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.material_usage import MaterialUsage
from app.repositories.material_usage_repository import SqlMaterialUsageRepository


def _session(rows=()):
    s = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(rows)
    result.all.return_value = list(rows)
    s.execute = AsyncMock(return_value=result)
    s.add_all = MagicMock()
    s.flush = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_upsert_list_totals():
    s = _session([("m1", 1030, 1000)])
    repo = SqlMaterialUsageRepository(s)
    rows = [
        MaterialUsage(material_id="m1", product_id=None, period=date(2026, 1, 1), standard_usage=1, actual_usage=1),
        MaterialUsage(material_id="m1", product_id="p1", period=date(2026, 1, 1), standard_usage=1, actual_usage=1),
    ]
    assert await repo.upsert(rows) == 2
    s.add_all.assert_called_once_with(rows)
    assert await repo.totals_by_material(["m1"]) == {"m1": (1030.0, 1000.0)}
    await repo.list("m1")
    await repo.list()
