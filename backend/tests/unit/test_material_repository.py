"""
Fase 2 — SqlMaterialRepository dengan AsyncSession di-mock (tanpa DB nyata).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.material_repository import SqlMaterialRepository


def _session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.get = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    s.delete = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_list_mengembalikan_scalars():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a", "b"]
    session.execute.return_value = result

    repo = SqlMaterialRepository(session)

    assert await repo.list() == ["a", "b"]


@pytest.mark.asyncio
async def test_get_by_id_delegasi_session_get():
    session = _session()
    session.get.return_value = "mat"

    repo = SqlMaterialRepository(session)

    assert await repo.get_by_id("id-1") == "mat"
    session.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_code_scalar_one_or_none():
    session = _session()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    repo = SqlMaterialRepository(session)

    assert await repo.get_by_code("RM-001") is None


@pytest.mark.asyncio
async def test_add_flush_refresh():
    session = _session()
    repo = SqlMaterialRepository(session)
    material = object()

    returned = await repo.add(material)

    assert returned is material
    session.add.assert_called_once_with(material)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(material)


@pytest.mark.asyncio
async def test_save_flush_refresh():
    session = _session()
    repo = SqlMaterialRepository(session)
    material = object()

    await repo.save(material)

    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(material)


@pytest.mark.asyncio
async def test_delete_delegasi():
    session = _session()
    repo = SqlMaterialRepository(session)
    material = object()

    await repo.delete(material)

    session.delete.assert_awaited_once_with(material)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_map_codes_to_ids_kosong_tanpa_query():
    session = _session()
    repo = SqlMaterialRepository(session)

    assert await repo.map_codes_to_ids(set()) == {}
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_map_codes_to_ids_mengembalikan_peta():
    session = _session()
    result = MagicMock()
    result.all.return_value = [("RM-001", "id-1"), ("RM-002", "id-2")]
    session.execute.return_value = result
    repo = SqlMaterialRepository(session)

    mapping = await repo.map_codes_to_ids({"RM-001", "RM-002"})

    assert mapping == {"RM-001": "id-1", "RM-002": "id-2"}
