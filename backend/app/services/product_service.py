"""
ProductService — CRUD master data produk jadi + import CSV (Fase 2 v3.0).

Mirror MaterialService (repo injectable, model_factory memisahkan pembuatan ORM
dari logika bisnis untuk test). `code` unik → ProductCodeExistsError.
"""
import csv as csv_module
import io
from typing import Callable, Protocol

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.exceptions import (
    ProductCodeExistsError,
    ProductNotFoundError,
    UploadInvalidFormatError,
)

REQUIRED_IMPORT_COLUMNS = {"code", "name", "unit"}


class _ProductRepository(Protocol):
    async def list(self): ...
    async def get_by_id(self, product_id: str): ...
    async def get_by_code(self, code: str): ...
    async def add(self, product): ...
    async def save(self, product): ...
    async def delete(self, product): ...


class ProductService:
    def __init__(self, repo: _ProductRepository, model_factory: Callable[..., object] = Product):
        self._repo = repo
        self._model = model_factory

    async def list(self):
        return await self._repo.list()

    async def get(self, product_id: str):
        product = await self._repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError("Produk tidak ditemukan.")
        return product

    async def create(self, payload: ProductCreate):
        if await self._repo.get_by_code(payload.code) is not None:
            raise ProductCodeExistsError(f"Kode produk '{payload.code}' sudah dipakai.")
        product = self._model(**payload.model_dump())
        return await self._repo.add(product)

    async def update(self, product_id: str, payload: ProductUpdate):
        product = await self.get(product_id)
        changes = payload.model_dump(exclude_unset=True)

        new_code = changes.get("code")
        if new_code and new_code != product.code:
            existing = await self._repo.get_by_code(new_code)
            if existing is not None and getattr(existing, "id", None) != product.id:
                raise ProductCodeExistsError(f"Kode produk '{new_code}' sudah dipakai.")

        for field, value in changes.items():
            setattr(product, field, value)
        return await self._repo.save(product)

    async def delete(self, product_id: str) -> None:
        product = await self.get(product_id)
        await self._repo.delete(product)

    async def import_csv(self, content: bytes) -> dict:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UploadInvalidFormatError("File bukan CSV UTF-8 yang valid.") from exc

        reader = csv_module.DictReader(io.StringIO(text))
        headers = {h.strip() for h in (reader.fieldnames or [])}
        missing = REQUIRED_IMPORT_COLUMNS - headers
        if missing:
            raise UploadInvalidFormatError(f"Kolom wajib hilang: {', '.join(sorted(missing))}.")

        rows = [self._parse_row(row, i) for i, row in enumerate(reader, start=2)]
        if not rows:
            raise UploadInvalidFormatError("File tidak berisi baris data.")

        seen: set[str] = set()
        for payload in rows:
            if payload.code in seen:
                raise ProductCodeExistsError(f"Kode '{payload.code}' muncul lebih dari sekali di file.")
            seen.add(payload.code)

        for payload in rows:
            await self.create(payload)
        return {"imported": len(rows)}

    def _parse_row(self, row: dict, line: int) -> ProductCreate:
        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()
        unit = (row.get("unit") or "").strip()
        if not code or not name or not unit:
            raise UploadInvalidFormatError(f"Baris {line}: code/name/unit tidak boleh kosong.")
        return ProductCreate(
            code=code,
            name=name,
            category=(row.get("category") or "").strip() or None,
            unit=unit,
        )
