"""
Fase 5 — SqlReorderRepository dengan AsyncSession di-mock.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.reorder_repository import SqlReorderRepository


def _session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.add_all = MagicMock()
    s.flush = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_replace_for_run_hapus_lalu_tambah():
    session = _session()
    repo = SqlReorderRepository(session)
    recs = [object(), object()]

    count = await repo.replace_for_run("r1", recs)

    assert count == 2
    session.execute.assert_awaited_once()  # DELETE lama
    session.add_all.assert_called_once_with(recs)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_replace_for_run_kosong_tanpa_add_all():
    session = _session()
    repo = SqlReorderRepository(session)

    count = await repo.replace_for_run("r1", [])

    assert count == 0
    session.add_all.assert_not_called()


@pytest.mark.asyncio
async def test_list_by_run():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a", "b"]
    session.execute.return_value = result
    repo = SqlReorderRepository(session)

    assert await repo.list_by_run("r1") == ["a", "b"]
