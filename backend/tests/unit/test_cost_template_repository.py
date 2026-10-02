"""
Fase 10 — SqlCostTemplateRepository dengan AsyncSession di-mock (tanpa DB nyata).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.repositories.cost_template_repository import SqlCostTemplateRepository


def _session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.get = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    s.delete = AsyncMock()
    return s


def _sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect())).replace("\n", " ")


@pytest.mark.asyncio
async def test_list_urut_nama():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a", "b"]
    session.execute.return_value = result
    assert await SqlCostTemplateRepository(session).list() == ["a", "b"]
    assert "ORDER BY cost_templates.name" in _sql(session.execute.await_args.args[0])


@pytest.mark.asyncio
async def test_get_by_id_delegasi_session_get():
    session = _session()
    session.get.return_value = "tpl"
    assert await SqlCostTemplateRepository(session).get_by_id("t1") == "tpl"


@pytest.mark.asyncio
async def test_get_by_name_dan_get_active_scalar_one_or_none():
    session = _session()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    repo = SqlCostTemplateRepository(session)
    assert await repo.get_by_name("X") is None
    assert "cost_templates.name =" in _sql(session.execute.await_args.args[0])
    assert await repo.get_active() is None
    assert "cost_templates.is_active IS true" in _sql(session.execute.await_args.args[0])


@pytest.mark.asyncio
async def test_add_flush_lalu_refresh_items():
    session = _session()
    tpl = object()
    assert await SqlCostTemplateRepository(session).add(tpl) is tpl
    session.add.assert_called_once_with(tpl)
    session.flush.assert_awaited_once()
    assert "items" in session.refresh.await_args.kwargs["attribute_names"]


@pytest.mark.asyncio
async def test_save_refresh_items():
    session = _session()
    tpl = object()
    assert await SqlCostTemplateRepository(session).save(tpl) is tpl
    assert "items" in session.refresh.await_args.kwargs["attribute_names"]


@pytest.mark.asyncio
async def test_set_active_matikan_yang_lain_dulu_baru_aktifkan():
    session = _session()
    await SqlCostTemplateRepository(session).set_active("t2")
    first, second = (c.args[0] for c in session.execute.await_args_list)
    sql1, sql2 = _sql(first), _sql(second)
    # 1) yang aktif selain t2 → false; 2) t2 → true. Urutan ini menjaga partial
    #    unique index (maksimal satu is_active) tidak pernah dilanggar.
    assert "SET is_active=" in sql1 and "is_active IS true" in sql1 and "cost_templates.id !=" in sql1
    assert first.compile().params["is_active"] is False
    assert "SET is_active=" in sql2 and "cost_templates.id =" in sql2
    assert second.compile().params["is_active"] is True
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete():
    session = _session()
    tpl = object()
    await SqlCostTemplateRepository(session).delete(tpl)
    session.delete.assert_awaited_once_with(tpl)
    session.flush.assert_awaited_once()
