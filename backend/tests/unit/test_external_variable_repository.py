"""Fase 11.2b — SqlExternalVariableRepository dengan AsyncSession di-mock (tanpa DB nyata)."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.models.external_variable import ExternalVariable, ExternalVariableValue
from app.repositories.external_variable_repository import SqlExternalVariableRepository


def _session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.get = AsyncMock()
    s.add = MagicMock()
    s.add_all = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    s.delete = AsyncMock()
    return s


def _sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect())).replace("\n", " ")


def _scalars(session, items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalar_one_or_none.return_value = items[0] if items else None
    result.all.return_value = items
    result.rowcount = len(items)
    session.execute.return_value = result


@pytest.mark.asyncio
async def test_list_dan_list_active():
    s = _session()
    _scalars(s, ["a"])
    repo = SqlExternalVariableRepository(s)
    assert await repo.list() == ["a"]
    assert await repo.list_active() == ["a"]
    assert "is_active IS true" in _sql(s.execute.await_args.args[0])


@pytest.mark.asyncio
async def test_get_by_id_code_add_save_delete():
    s = _session()
    s.get.return_value = "v"
    repo = SqlExternalVariableRepository(s)
    assert await repo.get_by_id("v1") == "v"
    _scalars(s, [])
    assert await repo.get_by_code("suhu") is None
    var = ExternalVariable(code="suhu", name="Suhu")
    assert await repo.add(var) is var
    assert await repo.save(var) is var
    await repo.delete(var)
    s.delete.assert_awaited_once_with(var)


@pytest.mark.asyncio
async def test_upsert_values_hapus_kunci_sama_lalu_insert():
    s = _session()
    rows = [
        ExternalVariableValue(variable_id="v1", product_id=None, period=date(2026, 1, 1), value=1),
        ExternalVariableValue(variable_id="v2", product_id="p1", period=date(2026, 1, 1), value=1),
    ]
    assert await SqlExternalVariableRepository(s).upsert_values(rows) == 2
    sqls = [_sql(c.args[0]) for c in s.execute.await_args_list]
    assert "product_id IS NULL" in sqls[0]
    assert "product_id =" in sqls[1]
    s.add_all.assert_called_once_with(rows)


@pytest.mark.asyncio
async def test_values_queries():
    s = _session()
    _scalars(s, [("v1", 3)])
    repo = SqlExternalVariableRepository(s)
    assert await repo.count_values() == {"v1": 3}
    await repo.list_values("v1", "p1")
    assert "product_id" in _sql(s.execute.await_args.args[0])
    assert await repo.values_for([], "p1") == []
    await repo.values_for(["v1"], "p1")
    assert "product_id IS NULL OR" in _sql(s.execute.await_args.args[0])
    assert await repo.delete_values("v1") == 1
