"""
BomService — CRUD master data Bill of Materials + import CSV (Fase 2 v3.0).

Setiap baris BOM merujuk `product_id` + `material_id` yang HARUS ada di master data
(ProductNotFoundError / MaterialNotFoundError bila tidak).

Hasil forecast TIDAK diturunkan ke BOM/material (lihat docs/RECONCILIATION.md
§"Forecast produk-only"). BOM di sini hanya dipakai master data + reorder/cost.
"""
import csv as csv_module
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable, Protocol

from app.models.bom import Bom
from app.schemas.bom import BomCreate, BomUpdate
from app.utils.exceptions import (
    BomNotFoundError,
    MaterialNotFoundError,
    ProductNotFoundError,
    UploadInvalidFormatError,
)

REQUIRED_IMPORT_COLUMNS = {"product_code", "material_code", "qty_per_unit"}


# ── Breakdown deret & buffer stock — fungsi murni, dipakai reorder & cost ──


@dataclass
class BomLine:
    """Baris BOM ringkas untuk kalkulasi breakdown (id sebagai string)."""
    product_id: str
    material_id: str
    qty_per_unit: float


def breakdown_requirements_series(
    product_series: dict[str, list[float]], bom_lines: list[BomLine]
) -> dict[str, list[float]]:
    """
    Dari deret forecast tiap produk, hasilkan deret kebutuhan per material
    (dipakai reorder & cost untuk μ/σ, EOQ, dan biaya).
      material_series[t] = Σ_produk (produk_series[t] × qty_per_unit)
    Produk tanpa deret diabaikan; panjang deret material = deret produk terpanjang.
    """
    series: dict[str, list[float]] = {}
    for line in bom_lines:
        values = product_series.get(line.product_id)
        if not values:
            continue
        target = series.setdefault(line.material_id, [])
        if len(target) < len(values):
            target.extend([0.0] * (len(values) - len(target)))
        for t, v in enumerate(values):
            target[t] += float(v) * float(line.qty_per_unit)
    return series


def compute_standard_usage(output_produksi: float, bom_qty_per_unit: float) -> float:
    """Standar Pemakaian Material = Output Produksi × BOM (per unit produk)."""
    return float(output_produksi) * float(bom_qty_per_unit)


def compute_buffer_stock(standard_usage: float, actual_usage: float) -> tuple[float, float]:
    """
    Buffer Stock = Standar Pemakaian − Aktual Pemakaian (kuantitas, tak negatif).
    buffer_pct = (standar − aktual) / standar × 100 (0 bila standar 0).
    Mengantisipasi waste produksi (Bab III thesis).
    """
    standard, actual = float(standard_usage), float(actual_usage)
    buffer_qty = max(0.0, standard - actual)
    buffer_pct = ((standard - actual) / standard * 100) if standard != 0 else 0.0
    return buffer_qty, buffer_pct


class _Repo(Protocol):
    async def list(self, product_id: str | None = None): ...
    async def get_by_id(self, bom_id: str): ...
    async def add(self, bom): ...
    async def save(self, bom): ...
    async def delete(self, bom): ...


class BomService:
    def __init__(self, repo: _Repo, products, materials, model_factory: Callable[..., object] = Bom):
        self._repo = repo
        self._products = products
        self._materials = materials
        self._model = model_factory

    async def list(self, product_id: str | None = None):
        return await self._repo.list(product_id)

    async def get(self, bom_id: str):
        bom = await self._repo.get_by_id(bom_id)
        if bom is None:
            raise BomNotFoundError("Baris BOM tidak ditemukan.")
        return bom

    async def _require_refs(self, product_id: str, material_id: str) -> None:
        if await self._products.get_by_id(product_id) is None:
            raise ProductNotFoundError(f"Produk '{product_id}' tidak ditemukan.")
        if await self._materials.get_by_id(material_id) is None:
            raise MaterialNotFoundError(f"Material '{material_id}' tidak ditemukan.")

    async def create(self, payload: BomCreate):
        await self._require_refs(payload.product_id, payload.material_id)
        bom = self._model(**payload.model_dump())
        return await self._repo.add(bom)

    async def update(self, bom_id: str, payload: BomUpdate):
        bom = await self.get(bom_id)
        changes = payload.model_dump(exclude_unset=True)
        product_id = changes.get("product_id", str(bom.product_id))
        material_id = changes.get("material_id", str(bom.material_id))
        if "product_id" in changes or "material_id" in changes:
            await self._require_refs(product_id, material_id)
        for field, value in changes.items():
            setattr(bom, field, value)
        return await self._repo.save(bom)

    async def delete(self, bom_id: str) -> None:
        bom = await self.get(bom_id)
        await self._repo.delete(bom)

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

        raw_rows = list(enumerate(reader, start=2))
        if not raw_rows:
            raise UploadInvalidFormatError("File tidak berisi baris data.")

        imported = 0
        for line, row in raw_rows:
            product_code = (row.get("product_code") or "").strip()
            material_code = (row.get("material_code") or "").strip()
            qty_raw = (row.get("qty_per_unit") or "").strip()
            if not product_code or not material_code or not qty_raw:
                raise UploadInvalidFormatError(
                    f"Baris {line}: product_code/material_code/qty_per_unit tidak boleh kosong."
                )
            try:
                qty = Decimal(qty_raw)
            except InvalidOperation as exc:
                raise UploadInvalidFormatError(f"Baris {line}: 'qty_per_unit' bukan angka valid.") from exc

            product = await self._products.get_by_code(product_code)
            if product is None:
                raise ProductNotFoundError(f"Baris {line}: produk '{product_code}' belum terdaftar.")
            material = await self._materials.get_by_code(material_code)
            if material is None:
                raise MaterialNotFoundError(f"Baris {line}: material '{material_code}' belum terdaftar.")

            await self.create(
                BomCreate(product_id=str(product.id), material_id=str(material.id), qty_per_unit=qty)
            )
            imported += 1
        return {"imported": imported}
