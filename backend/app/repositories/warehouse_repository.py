"""
Warehouse repositories (v3.0 Fase 6, redesain 24 Agustus 2026) —
docs/ARCHITECTURE.md §4. `WarehouseConfig` kini satu baris per produk (pola CRUD
sama seperti `bom_repository.py`), bukan satu baris global per kategori.
"""
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import WarehouseConfig, WarehouseValidation


class SqlWarehouseConfigRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self) -> list[WarehouseConfig]:
        result = await self._session.execute(
            select(WarehouseConfig).order_by(WarehouseConfig.created_at)
        )
        return list(result.scalars().all())

    async def get_by_id(self, config_id: str) -> WarehouseConfig | None:
        return await self._session.get(WarehouseConfig, config_id)

    async def get_by_product(self, product_id: str) -> WarehouseConfig | None:
        result = await self._session.execute(
            select(WarehouseConfig).where(WarehouseConfig.product_id == product_id)
        )
        return result.scalar_one_or_none()

    async def add(self, config: WarehouseConfig) -> WarehouseConfig:
        self._session.add(config)
        await self._session.flush()
        await self._session.refresh(config)
        return config

    async def save(self, config: WarehouseConfig) -> WarehouseConfig:
        await self._session.flush()
        await self._session.refresh(config)
        return config

    async def delete(self, config: WarehouseConfig) -> None:
        await self._session.delete(config)
        await self._session.flush()


class SqlWarehouseValidationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def replace_for_run(self, run_id: str, validation: WarehouseValidation) -> WarehouseValidation:
        await self._session.execute(
            delete(WarehouseValidation).where(WarehouseValidation.run_id == run_id)
        )
        self._session.add(validation)
        await self._session.flush()
        await self._session.refresh(validation)
        return validation

    async def get_for_run(self, run_id: str) -> WarehouseValidation | None:
        result = await self._session.execute(
            select(WarehouseValidation).where(WarehouseValidation.run_id == run_id)
        )
        return result.scalar_one_or_none()
