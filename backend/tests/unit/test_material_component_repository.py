"""Fase 11.3 — SqlMaterialComponentRepository (AsyncSession di-mock)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.material_component import MaterialComponent
from app.repositories.material_component_repository import SqlMaterialComponentRepository


@pytest.mark.asyncio
async def test_crud():
    s = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["c"]
    s.execute = AsyncMock(return_value=result)
    s.get = AsyncMock(return_value="c")
    s.add, s.flush, s.refresh, s.delete = MagicMock(), AsyncMock(), AsyncMock(), AsyncMock()
    repo = SqlMaterialComponentRepository(s)

    assert await repo.list("btl") == ["c"] and await repo.list() == ["c"]
    assert await repo.get_by_id("c1") == "c"
    row = MaterialComponent(parent_material_id="a", component_material_id="b", qty_per_unit=1)
    assert await repo.add(row) is row
    await repo.delete(row)
    s.delete.assert_awaited_once_with(row)
