"""
ProductRepository — akses tabel `products` (docs/ARCHITECTURE.md §4).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class SqlProductRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list(self) -> list[Product]:
        result = await self._session.execute(select(Product).order_by(Product.code))
        return list(result.scalars().all())

    async def get_by_id(self, product_id: str) -> Product | None:
        return await self._session.get(Product, product_id)

    async def get_by_code(self, code: str) -> Product | None:
        result = await self._session.execute(select(Product).where(Product.code == code))
        return result.scalar_one_or_none()

    async def map_codes_to_ids(self, codes: set[str]) -> dict[str, str]:
        if not codes:
            return {}
        result = await self._session.execute(
            select(Product.code, Product.id).where(Product.code.in_(codes))
        )
        return {code: str(pid) for code, pid in result.all()}

    async def add(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def save(self, product: Product) -> Product:
        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def delete(self, product: Product) -> None:
        await self._session.delete(product)
        await self._session.flush()
