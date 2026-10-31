"""
Repository variabel eksternal (Fase 11.2b) — master + nilai per periode.
`upsert_values` menimpa nilai dengan kunci (variable, product, period) yang sama.
"""
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_variable import ExternalVariable, ExternalVariableValue


class SqlExternalVariableRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self) -> list[ExternalVariable]:
        result = await self._session.execute(select(ExternalVariable).order_by(ExternalVariable.code))
        return list(result.scalars().all())

    async def list_active(self) -> list[ExternalVariable]:
        result = await self._session.execute(
            select(ExternalVariable).where(ExternalVariable.is_active.is_(True)).order_by(ExternalVariable.code)
        )
        return list(result.scalars().all())

    async def get_by_id(self, variable_id) -> ExternalVariable | None:
        return await self._session.get(ExternalVariable, variable_id)

    async def get_by_code(self, code: str) -> ExternalVariable | None:
        result = await self._session.execute(select(ExternalVariable).where(ExternalVariable.code == code))
        return result.scalar_one_or_none()

    async def add(self, variable: ExternalVariable) -> ExternalVariable:
        self._session.add(variable)
        await self._session.flush()
        await self._session.refresh(variable)
        return variable

    async def save(self, variable: ExternalVariable) -> ExternalVariable:
        await self._session.flush()
        await self._session.refresh(variable)
        return variable

    async def delete(self, variable: ExternalVariable) -> None:
        await self._session.delete(variable)  # nilai ikut terhapus (ON DELETE CASCADE)
        await self._session.flush()

    async def upsert_values(self, rows: list[ExternalVariableValue]) -> int:
        for r in rows:
            product_cond = (
                ExternalVariableValue.product_id.is_(None)
                if r.product_id is None
                else ExternalVariableValue.product_id == r.product_id
            )
            await self._session.execute(
                delete(ExternalVariableValue).where(
                    ExternalVariableValue.variable_id == r.variable_id,
                    ExternalVariableValue.period == r.period,
                    product_cond,
                )
            )
        self._session.add_all(rows)
        await self._session.flush()
        return len(rows)

    async def list_values(self, variable_id, product_id=None) -> list[ExternalVariableValue]:
        stmt = select(ExternalVariableValue).where(ExternalVariableValue.variable_id == variable_id)
        if product_id is not None:
            stmt = stmt.where(ExternalVariableValue.product_id == product_id)
        result = await self._session.execute(stmt.order_by(ExternalVariableValue.period))
        return list(result.scalars().all())

    async def delete_values(self, variable_id) -> int:
        result = await self._session.execute(
            delete(ExternalVariableValue).where(ExternalVariableValue.variable_id == variable_id)
        )
        await self._session.flush()
        return result.rowcount or 0

    async def values_for(self, variable_ids, product_id) -> list[ExternalVariableValue]:
        if not variable_ids:
            return []
        result = await self._session.execute(
            select(ExternalVariableValue).where(
                and_(
                    ExternalVariableValue.variable_id.in_(list(variable_ids)),
                    or_(ExternalVariableValue.product_id.is_(None), ExternalVariableValue.product_id == product_id),
                )
            )
        )
        return list(result.scalars().all())

    async def count_values(self) -> dict[str, int]:
        result = await self._session.execute(
            select(ExternalVariableValue.variable_id, func.count()).group_by(ExternalVariableValue.variable_id)
        )
        return {str(vid): int(n) for vid, n in result.all()}
