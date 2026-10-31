"""
MaterialUsageService (Fase 11.1, 30 Oktober 2026) — import pemakaian aktual material dan
faktor waste per material untuk buffer stock (REVISI_V2 §3.8, Keputusan #8).

Import (CSV/XLSX): material_code, period, actual_usage, dan salah satu:
  - standard_usage (diisi langsung), atau
  - product_code + production_output → standar = output × qty BOM(produk, material)
Kunci (material, produk, periode) yang sama ditimpa.

Faktor waste = Σ aktual ÷ Σ standar seluruh periode tersimpan (agregat, bukan rata-rata
rasio — periode bervolume kecil tidak mendominasi). Standar 0 → None.
"""
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

import pandas as pd

from app.models.material_usage import MaterialUsage
from app.services.bom_service import compute_standard_usage, compute_waste_factor
from app.utils.exceptions import UploadInvalidFormatError
from app.utils.tabular import cell, read_table, require_columns


class MaterialUsageService:
    def __init__(self, repo, materials, products, boms, factory: Callable[..., object] = MaterialUsage):
        self._repo = repo
        self._materials = materials
        self._products = products
        self._boms = boms
        self._factory = factory

    async def list(self, material_id: str | None = None):
        return await self._repo.list(material_id)

    async def waste_factors(self, material_ids=None) -> dict[str, float | None]:
        totals = await self._repo.totals_by_material(material_ids)
        return {mid: compute_waste_factor(actual, standard) for mid, (actual, standard) in totals.items()}

    async def import_usage(self, filename: str, content: bytes) -> dict:
        df = read_table(filename, content)
        require_columns(df, {"material_code", "period", "actual_usage"})
        if df.empty:
            raise UploadInvalidFormatError("File tidak berisi baris data.")

        cache: dict[tuple[str, str], object] = {}

        async def lookup(kind: str, repo, code: str):
            if (kind, code) not in cache:
                cache[(kind, code)] = await repo.get_by_code(code)
            return cache[(kind, code)]

        def number(raw, name: str, line: int) -> Decimal | None:
            text = cell(raw)
            if text == "":
                return None
            try:
                value = Decimal(text)
            except InvalidOperation as exc:
                raise UploadInvalidFormatError(f"Baris {line}: '{name}' bukan angka valid.") from exc
            if value < 0:
                raise UploadInvalidFormatError(f"Baris {line}: '{name}' tidak boleh negatif.")
            return value

        rows = []
        for i, raw in enumerate(df.to_dict("records"), start=2):
            code = cell(raw.get("material_code"))
            material = await lookup("material", self._materials, code)
            if material is None:
                raise UploadInvalidFormatError(f"Baris {i}: Material '{code}' tidak ditemukan.")
            try:
                period = pd.to_datetime(cell(raw.get("period"))).date()
            except (ValueError, TypeError) as exc:
                raise UploadInvalidFormatError(f"Baris {i}: 'period' bukan tanggal valid.") from exc

            actual = number(raw.get("actual_usage"), "actual_usage", i)
            if actual is None:
                raise UploadInvalidFormatError(f"Baris {i}: 'actual_usage' wajib diisi.")
            standard = number(raw.get("standard_usage"), "standard_usage", i)
            output = number(raw.get("production_output"), "production_output", i)
            product_code = cell(raw.get("product_code"))
            product_id = None

            if product_code:
                product = await lookup("product", self._products, product_code)
                if product is None:
                    raise UploadInvalidFormatError(f"Baris {i}: Produk '{product_code}' tidak ditemukan.")
                product_id = product.id
            if standard is None:
                if output is None or product_id is None:
                    raise UploadInvalidFormatError(
                        f"Baris {i}: isi standard_usage, atau product_code + production_output."
                    )
                line = next(
                    (b for b in await self._boms.list(str(product_id)) if str(b.material_id) == str(material.id)),
                    None,
                )
                if line is None:
                    raise UploadInvalidFormatError(
                        f"Baris {i}: BOM {product_code} → {code} belum ada; standar tidak bisa dihitung."
                    )
                standard = Decimal(str(compute_standard_usage(float(output), float(line.qty_per_unit))))

            rows.append(
                self._factory(
                    material_id=material.id,
                    product_id=product_id,
                    period=period,
                    production_output=output,
                    standard_usage=standard,
                    actual_usage=actual,
                )
            )
        return {"imported": await self._repo.upsert(rows)}
