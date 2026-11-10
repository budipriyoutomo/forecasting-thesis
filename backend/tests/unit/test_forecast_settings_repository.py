"""
Fase 11.2a — SqlForecastSettingsRepository dengan AsyncSession di-mock (tanpa DB nyata).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.forecast_setting import ForecastSetting
from app.repositories.forecast_settings_repository import SqlForecastSettingsRepository


def _session():
    s = MagicMock()
    s.get = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.refresh = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_get_baris_singleton_id_1():
    session = _session()
    session.get.return_value = "row"

    assert await SqlForecastSettingsRepository(session).get() == "row"
    session.get.assert_awaited_once_with(ForecastSetting, 1)


@pytest.mark.asyncio
async def test_save_add_flush_refresh():
    session = _session()
    row = ForecastSetting(id=1, display_metrics=["mape"])

    assert await SqlForecastSettingsRepository(session).save(row) is row
    session.add.assert_called_once_with(row)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(row, attribute_names=["updated_at"])
