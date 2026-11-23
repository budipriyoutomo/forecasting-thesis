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
from decimal import Decimal

from app.models.material_usage import MaterialUsage
from app.services.bom_service import compute_standard_usage, compute_waste_factor
from app.utils.exceptions import UploadInvalidFormatError
from app.utils.tabular import cell, is_blank_row, parse_decimal_id, parse_iso_date, read_table, require_columns

# Kolom Numeric(18, 4) → bagian bulat maksimal 14 digit; lebih dari itu ditolak DB (500).
_MAX_VALUE = Decimal(10) ** 14


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
        # Nomor baris file (header = 1) dihitung sebelum baris kosong di tengah dilewati.
        records = [(i, r) for i, r in enumerate(df.to_dict("records"), start=2) if not is_blank_row(r)]
        if not records:
            raise UploadInvalidFormatError("File tidak berisi baris data.")

        cache: dict[tuple[str, str], object] = {}

        async def lookup(kind: str, repo, code: str):
            if (kind, code) not in cache:
                cache[(kind, code)] = await repo.get_by_code(code)
            return cache[(kind, code)]

        def number(raw, name: str, line: int) -> Decimal | None:
            try:
                value = parse_decimal_id(raw)  # desimal titik atau koma (CSV Excel Indonesia)
            except ValueError as exc:
                raise UploadInvalidFormatError(f"Baris {line}: '{name}' bukan angka valid.") from exc
            if value is None:
                return None
            if value < 0:
                raise UploadInvalidFormatError(f"Baris {line}: '{name}' tidak boleh negatif.")
            if value >= _MAX_VALUE:
                raise UploadInvalidFormatError(f"Baris {line}: '{name}' terlalu besar.")
            return value

        seen: dict[tuple, int] = {}

        rows = []
        for i, raw in records:
            code = cell(raw.get("material_code"))
            if code == "":
                raise UploadInvalidFormatError(f"Baris {i}: 'material_code' wajib diisi.")
            material = await lookup("material", self._materials, code)
            if material is None:
                raise UploadInvalidFormatError(f"Baris {i}: Material '{code}' tidak ditemukan.")
            try:
                period = parse_iso_date(raw.get("period"))
            except ValueError as exc:
                raise UploadInvalidFormatError(
                    f"Baris {i}: 'period' bukan tanggal valid (format YYYY-MM-DD)."
                ) from exc
            if period is None:
                raise UploadInvalidFormatError(f"Baris {i}: 'period' wajib diisi (format YYYY-MM-DD).")

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
                if standard >= _MAX_VALUE:
                    raise UploadInvalidFormatError(f"Baris {i}: standar hasil output × BOM terlalu besar.")

            # Unique index (material, [produk], periode): duplikat dalam satu file → IntegrityError.
            key = (str(material.id), str(product_id), period)
            if key in seen:
                raise UploadInvalidFormatError(
                    f"Baris {i}: duplikat material {code}"
                    + (f" / produk {product_code}" if product_id else "")
                    + f" periode {period} dengan baris {seen[key]}."
                )
            seen[key] = i

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
