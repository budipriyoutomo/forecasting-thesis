"""Fase 11.6 — SqlStockProjectionRepository (AsyncSession di-mock)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.stock_projection_repository import SqlStockProjectionRepository


@pytest.mark.asyncio
async def test_replace_dan_list():
    s = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["row"]
    s.execute, s.flush, s.add_all = AsyncMock(return_value=result), AsyncMock(), MagicMock()
    repo = SqlStockProjectionRepository(s)
    assert await repo.replace_for_run("r1", ["a", "b"]) == 2
    s.add_all.assert_called_once_with(["a", "b"])
    assert await repo.list_by_run("r1") == ["row"]
