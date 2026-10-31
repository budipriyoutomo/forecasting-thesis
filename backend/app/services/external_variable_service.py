"""
ExternalVariableService (Fase 11.2b, 30 Oktober 2026) — master data variabel eksternal
dinamis + import nilai per periode + penyusun matriks exog untuk engine ML.

Keputusan #7 (docs/REVISI_V2.md §6.1): musim, cuaca & temperatur, harga, promosi & event
tersedia → planner mendefinisikan variabel sendiri dan bisa (de)aktivasi. Engine hanya
memakai variabel AKTIF yang nilainya lengkap untuk histori + horizon (lihat engines/_ml.py).

Import (CSV/XLSX): variable_code, period, value [, product_code]
  - scope product → product_code wajib; scope global → product_code harus kosong
  - value_type flag → value 0/1
  - nilai dengan kunci (variabel, produk, periode) yang sama ditimpa
"""
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

import pandas as pd

from app.models.external_variable import ExternalVariable, ExternalVariableValue
from app.utils.exceptions import (
    ExternalVariableCodeExistsError,
    ExternalVariableNotFoundError,
    UploadInvalidFormatError,
)
from app.utils.tabular import cell, read_table, require_columns

IMPORT_COLUMNS = {"variable_code", "period", "value"}


def build_exog(variables, values) -> pd.DataFrame | None:
    """Pivot nilai → DataFrame (index = periode, kolom = kode variabel, terurut).

    `values` sudah difilter untuk satu produk (baris global + baris produk itu).
    Variabel scope product hanya memakai baris ber-product_id; global baris tanpa.
    """
    if not variables:
        return None
    by_id = {str(v.id): v for v in variables}
    records = []
    for r in values:
        var = by_id.get(str(r.variable_id))
        if var is None:
            continue
        if (var.scope == "product") != (r.product_id is not None):
            continue
        records.append({"period": pd.Timestamp(r.period), "code": var.code, "value": float(r.value)})
    if not records:
        return None
    df = pd.DataFrame(records).pivot_table(index="period", columns="code", values="value", aggfunc="last")
    df = df.reindex(columns=sorted(v.code for v in variables if v.code in df.columns))
    df.columns.name = None
    return df.sort_index()


class ExternalVariableService:
    def __init__(
        self,
        repo,
        products,
        var_factory: Callable[..., object] = ExternalVariable,
        value_factory: Callable[..., object] = ExternalVariableValue,
    ):
        self._repo = repo
        self._products = products
        self._var = var_factory
        self._value = value_factory

    async def list(self):
        return await self._repo.list()

    async def value_counts(self) -> dict[str, int]:
        return await self._repo.count_values()

    async def get(self, variable_id: str):
        var = await self._repo.get_by_id(variable_id)
        if var is None:
            raise ExternalVariableNotFoundError("Variabel eksternal tidak ditemukan.")
        return var

    async def create(self, payload):
        if await self._repo.get_by_code(payload.code) is not None:
            raise ExternalVariableCodeExistsError(f"Kode variabel '{payload.code}' sudah dipakai.")
        return await self._repo.add(self._var(**payload.model_dump()))

    async def update(self, variable_id: str, payload):
        var = await self.get(variable_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(var, field, value)
        return await self._repo.save(var)

    async def delete(self, variable_id: str) -> None:
        await self._repo.delete(await self.get(variable_id))

    async def list_values(self, variable_id: str, product_id: str | None = None):
        await self.get(variable_id)
        return await self._repo.list_values(variable_id, product_id)

    async def clear_values(self, variable_id: str) -> int:
        await self.get(variable_id)
        return await self._repo.delete_values(variable_id)

    async def import_values(self, filename: str, content: bytes) -> dict:
        df = read_table(filename, content)
        require_columns(df, IMPORT_COLUMNS)
        if df.empty:
            raise UploadInvalidFormatError("File tidak berisi baris data.")

        variables: dict[str, object] = {}
        products: dict[str, object] = {}
        rows = []
        for i, raw in enumerate(df.to_dict("records"), start=2):
            code = cell(raw.get("variable_code"))
            if code not in variables:
                variables[code] = await self._repo.get_by_code(code)
            var = variables[code]
            if var is None:
                raise UploadInvalidFormatError(f"Baris {i}: variabel '{code}' tidak dikenal.")

            try:
                period = pd.to_datetime(cell(raw.get("period"))).date()
            except (ValueError, TypeError) as exc:
                raise UploadInvalidFormatError(f"Baris {i}: 'period' bukan tanggal valid.") from exc
            try:
                value = Decimal(cell(raw.get("value")))
            except InvalidOperation as exc:
                raise UploadInvalidFormatError(f"Baris {i}: 'value' bukan angka valid.") from exc
            if var.value_type == "flag" and value not in (0, 1):
                raise UploadInvalidFormatError(f"Baris {i}: variabel flag '{code}' harus bernilai 0 atau 1.")

            product_code = cell(raw.get("product_code"))
            product_id = None
            if var.scope == "product":
                if not product_code:
                    raise UploadInvalidFormatError(f"Baris {i}: product_code wajib untuk variabel per produk '{code}'.")
                if product_code not in products:
                    products[product_code] = await self._products.get_by_code(product_code)
                if products[product_code] is None:
                    raise UploadInvalidFormatError(f"Baris {i}: Produk '{product_code}' tidak ditemukan.")
                product_id = products[product_code].id
            elif product_code:
                raise UploadInvalidFormatError(
                    f"Baris {i}: variabel '{code}' bersifat global — kosongkan product_code."
                )

            rows.append(self._value(variable_id=var.id, product_id=product_id, period=period, value=value))

        return {"imported": await self._repo.upsert_values(rows)}

    async def exog_for_product(self, product_id) -> pd.DataFrame | None:
        """Matriks variabel AKTIF untuk satu produk (None bila tak ada)."""
        active = await self._repo.list_active()
        if not active:
            return None
        values = await self._repo.values_for([v.id for v in active], product_id)
        return build_exog(active, values)
