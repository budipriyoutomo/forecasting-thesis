"""
Fase 4 — SqlForecastRepository dengan AsyncSession di-mock.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.forecast_repository import SqlForecastRepository


def _session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.get = AsyncMock()
    s.add = MagicMock()
    s.add_all = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_add_run():
    session = _session()
    repo = SqlForecastRepository(session)
    run = object()

    assert await repo.add_run(run) is run
    session.add.assert_called_once_with(run)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(run)


@pytest.mark.asyncio
async def test_get_run():
    session = _session()
    session.get.return_value = "run"
    repo = SqlForecastRepository(session)

    assert await repo.get_run("r1") == "run"


@pytest.mark.asyncio
async def test_get_result():
    session = _session()
    session.get.return_value = "result"
    repo = SqlForecastRepository(session)

    assert await repo.get_result("fr1") == "result"


@pytest.mark.asyncio
async def test_save_run():
    session = _session()
    repo = SqlForecastRepository(session)
    run = object()

    assert await repo.save_run(run) is run
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_results():
    session = _session()
    repo = SqlForecastRepository(session)
    rows = [object(), object()]

    assert await repo.add_results(rows) == 2
    session.add_all.assert_called_once_with(rows)


@pytest.mark.asyncio
async def test_list_results():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a"]
    session.execute.return_value = result
    repo = SqlForecastRepository(session)

    assert await repo.list_results("r1") == ["a"]


@pytest.mark.asyncio
async def test_list_results_for_material():
    session = _session()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["a", "b"]
    session.execute.return_value = result
    repo = SqlForecastRepository(session)

    assert await repo.list_results_for_material("m1") == ["a", "b"]
