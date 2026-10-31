"""
Repository Pengaturan Forecast (Fase 11.2a) — satu baris global (id = 1).
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.forecast_setting import ForecastSetting


class SqlForecastSettingsRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self) -> ForecastSetting | None:
        return await self._session.get(ForecastSetting, 1)

    async def save(self, setting: ForecastSetting) -> ForecastSetting:
        self._session.add(setting)
        await self._session.flush()
        await self._session.refresh(setting, attribute_names=["updated_at"])
        return setting
