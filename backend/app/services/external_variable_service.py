"""
ExternalVariableService (Fase 11.2b, 30 Oktober 2026) — master data variabel eksternal
dinamis + import nilai per periode + penyusun matriks exog untuk engine ML.

Keputusan #7 (docs/REVISI_V2.md §6.1): musim, cuaca & temperatur, harga, promosi & event
tersedia → planner mendefinisikan variabel sendiri dan bisa (de)aktivasi. Engine hanya
memakai variabel AKTIF yang nilainya lengkap untuk histori + horizon (lihat engines/_ml.py).

Import (CSV/XLSX), dua format (deteksi otomatis, CR v3.4 §4.3):
  - panjang: variable_code, period, value [, product_code]
  - lebar (ada kolom `period`, tanpa `variable_code`): period [, product_code] + satu kolom per
    kode variabel — sesuai bentuk sheet Excel. Kolom tak dikenal → peringatan, bukan error.
    product_code hanya dipakai variabel per produk; variabel global mengabaikannya.
Aturan:
  - scope product → product_code wajib; format panjang: scope global → product_code harus kosong
  - value_type flag → value 0/1
  - angka toleran (`parse_decimal_id`): koma desimal, tab, `%`; sel kosong/`-`/`NA` dilewati
    dan dilaporkan per variabel
  - period dinormalisasi ke awal bulan (CR v3.4 §4.1, Excel thesis memakai tgl 24);
    baris ganda dengan tanggal SAMA → baris terakhir menang; tanggal BERBEDA di bulan yang sama
    → error (biasanya 'Jan-24' terbaca 24-Jan tahun berjalan, sehingga beberapa tahun melebur)
  - nilai dengan kunci (variabel, produk, periode) yang sama di DB ditimpa
  - semua error dikumpulkan; `dry_run` mengembalikan daftar error tanpa menulis apa pun,
    import biasa gagal seluruhnya bila ada satu error (all-or-nothing)
"""
# Kelas punya method `list` → tanpa ini anotasi list[...] rusak di Python 3.11 (VPS).
from __future__ import annotations

import io
from collections.abc import Callable
from datetime import date

import pandas as pd
from openpyxl import Workbook

from app.models.external_variable import ExternalVariable, ExternalVariableValue
from app.services.forecasting.preprocessing import normalize_period
from app.utils.exceptions import (
    ExternalVariableCodeExistsError,
    ExternalVariableNotFoundError,
    UploadInvalidFormatError,
)
from app.utils.tabular import cell, parse_decimal_id, read_table, require_columns

IMPORT_COLUMNS = {"variable_code", "period", "value"}
WIDE_ID_COLUMNS = {"period", "product_code"}
MAX_REPORTED_ERRORS = 100


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


def _category_code_warnings(variables: dict, rows) -> list[str]:
    """CR v3.4 §4.4 — variabel numerik yang nilainya hanya bilangan bulat 1..k (3 ≤ k ≤ 5)
    kemungkinan kode kategori nominal (mis. musim 1/2/3): model tree akan membaca urutan palsu.
    Hanya peringatan; import tetap jalan."""
    by_var: dict[str, set] = {}
    for r in rows:
        by_var.setdefault(str(r.variable_id), set()).add(r.value)
    out = []
    for code, var in variables.items():
        if var is None or var.value_type != "numeric":
            continue
        values = by_var.get(str(var.id), set())
        if 3 <= len(values) <= 5 and all(v == int(v) for v in values) and set(map(int, values)) == set(
            range(1, len(values) + 1)
        ):
            out.append(
                f"Variabel '{code}' hanya berisi bilangan bulat 1–{len(values)}: apakah ini kode kategori? "
                "Pertimbangkan satu variabel flag per kategori."
            )
    return out


class ExternalVariableService:
    def __init__(
        self,
        repo,
        products,
        *,
        demand=None,
        var_factory: Callable[..., object] = ExternalVariable,
        value_factory: Callable[..., object] = ExternalVariableValue,
    ):
        self._repo = repo
        self._products = products
        self._demand = demand
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

    async def _records(self, df: pd.DataFrame) -> tuple[str, list[tuple], list[str]]:
        """Baris file → (format, [(no_baris, kode, period, value_mentah, product_code)], peringatan)."""
        if "variable_code" in df.columns:
            require_columns(df, IMPORT_COLUMNS)
            records = [
                (i, cell(r.get("variable_code")), r.get("period"), r.get("value"), cell(r.get("product_code")))
                for i, r in enumerate(df.to_dict("records"), start=2)
            ]
            return "long", records, []

        if "period" not in df.columns:
            raise UploadInvalidFormatError(
                "Kolom wajib hilang: period (format lebar) atau variable_code, period, value (format panjang)."
            )
        known = {v.code for v in await self._repo.list()}
        var_columns = [c for c in df.columns if c not in WIDE_ID_COLUMNS]
        unknown = [c for c in var_columns if c not in known]
        warnings = [f"Kolom tidak dikenal diabaikan: {', '.join(unknown)}."] if unknown else []
        if not [c for c in var_columns if c in known]:
            raise UploadInvalidFormatError("Tidak ada kolom yang cocok dengan kode variabel eksternal.")
        records = [
            (i, code, r.get("period"), r.get(code), cell(r.get("product_code")))
            for i, r in enumerate(df.to_dict("records"), start=2)
            for code in var_columns
            if code in known
        ]
        return "wide", records, warnings

    async def import_values(self, filename: str, content: bytes, dry_run: bool = False) -> dict:
        df = read_table(filename, content)
        fmt, records, warnings = await self._records(df)
        if df.empty:
            raise UploadInvalidFormatError("File tidak berisi baris data.")

        variables: dict[str, object] = {}
        products: dict[str, object] = {}
        rows: dict[tuple, object] = {}  # (variable_id, product_id, period) → baris terakhir
        seen: dict[tuple, tuple[int, date]] = {}  # kunci → (baris pertama, tanggal asli)
        collided_rows: set[int] = set()  # format lebar: satu error bentrok per baris, bukan per kolom
        errors: list[str] = []
        skipped: dict[str, int] = {}
        normalized = overwritten = 0
        value_label = "'value'" if fmt == "long" else "kolom '{code}'"

        for i, code, raw_period, raw_value, product_code in records:
            if code not in variables:
                variables[code] = await self._repo.get_by_code(code)
            var = variables[code]
            if var is None:
                errors.append(f"Baris {i}: variabel '{code}' tidak dikenal.")
                continue

            try:
                value = parse_decimal_id(raw_value)
            except ValueError:
                errors.append(f"Baris {i}: {value_label.format(code=code)} bukan angka valid.")
                continue
            if value is None:
                skipped[code] = skipped.get(code, 0) + 1
                continue

            try:
                original = pd.to_datetime(cell(raw_period))
                period = normalize_period(original)
            except (ValueError, TypeError):
                errors.append(f"Baris {i}: 'period' bukan tanggal valid.")
                continue
            if var.value_type == "flag" and value not in (0, 1):
                errors.append(f"Baris {i}: variabel flag '{code}' harus bernilai 0 atau 1.")
                continue

            product_id = None
            if var.scope == "product":
                if not product_code:
                    errors.append(f"Baris {i}: product_code wajib untuk variabel per produk '{code}'.")
                    continue
                if product_code not in products:
                    products[product_code] = await self._products.get_by_code(product_code)
                if products[product_code] is None:
                    errors.append(f"Baris {i}: Produk '{product_code}' tidak ditemukan.")
                    continue
                product_id = products[product_code].id
            elif product_code and fmt == "long":
                errors.append(f"Baris {i}: variabel '{code}' bersifat global — kosongkan product_code.")
                continue

            key = (str(var.id), str(product_id), period)
            if key in seen and seen[key][1] != original.date():
                if i not in collided_rows:
                    collided_rows.add(i)
                    first_row, first_date = seen[key]
                    subject = f"'{code}' periode" if fmt == "long" else "periode"
                    errors.append(
                        f"Baris {i}: {subject} {original.date()} jatuh di bulan yang sama dengan baris "
                        f"{first_row} ({first_date}). Bila kolom period diketik 'Jan-24' (= Jan 2024) dan "
                        "terbaca 24-Jan, ubah jadi tanggal lengkap (2024-01-01) atau pakai template."
                    )
                continue
            seen.setdefault(key, (i, original.date()))
            normalized += original.date() != period
            overwritten += key in rows
            rows[key] = self._value(variable_id=var.id, product_id=product_id, period=period, value=value)

        warnings += _category_code_warnings(variables, rows.values())
        summary = {
            "format": fmt,
            "imported": len(rows),
            "normalized": normalized,
            "overwritten": overwritten,
            "skipped": skipped,
            "warnings": warnings,
        }
        if dry_run:
            return {
                **summary, "dry_run": True, "valid": not errors,
                "errors": errors[:MAX_REPORTED_ERRORS], "n_errors": len(errors),
            }
        if errors:
            more = f" (+{len(errors) - 1} error lain — pakai validasi dulu untuk daftar lengkap)" if len(errors) > 1 else ""
            raise UploadInvalidFormatError(errors[0] + more)
        summary["imported"] = await self._repo.upsert_values(list(rows.values()))
        return summary

    async def _expected_periods(self, horizon: int) -> list[date]:
        """Bulan pertama..terakhir demand (lintas produk) + `horizon` bulan; [] bila belum ada demand."""
        first, last = await self._demand.period_range() if self._demand else (None, None)
        if first is None:
            return []
        start = pd.Timestamp(normalize_period(first))
        end = pd.Timestamp(normalize_period(last)) + pd.DateOffset(months=horizon)
        return [ts.date() for ts in pd.date_range(start, end, freq="MS")]

    async def template(self, horizon: int) -> tuple[bytes, str]:
        """Template import format lebar (CR v3.4 §4.3): variabel AKTIF × periode demand + horizon,
        terisi nilai global yang sudah ada supaya planner cukup melengkapi sel kosong.
        Kolom product_code hanya muncul bila ada variabel aktif per produk (baris per produk
        ditambahkan planner sendiri)."""
        active = sorted(await self._repo.list_active(), key=lambda v: v.code)
        periods = await self._expected_periods(horizon)
        existing: dict[tuple[str, date], float] = {}
        if active:
            for r in await self._repo.values_for([v.id for v in active], None):
                if r.product_id is None:
                    existing[(str(r.variable_id), r.period)] = float(r.value)

        has_product = any(v.scope == "product" for v in active)
        headers = ["period", *(["product_code"] if has_product else []), *(v.code for v in active)]
        wb = Workbook()
        ws = wb.active
        ws.title = "nilai"
        ws.append(headers)
        for p in periods:
            ws.append([
                p, *([None] if has_product else []),
                *(existing.get((str(v.id), p)) if v.scope == "global" else None for v in active),
            ])
        for row in ws.iter_rows(min_row=2, max_col=1):
            row[0].number_format = "yyyy-mm-dd"

        info = wb.create_sheet("petunjuk")
        info.append(["kode", "nama", "tipe", "cakupan", "satuan"])
        for v in active:
            info.append([v.code, v.name, v.value_type, v.scope, v.unit])
        info.append([])
        info.append(["Kosongkan sel atau isi '-' bila nilai belum ada. Koma desimal & tanggal mana pun di bulan itu diterima."])
        if has_product:
            info.append(["Variabel per produk: tambahkan satu baris per produk & periode, isi product_code."])

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), "template_variabel_eksternal.xlsx"

    async def coverage(self, horizon: int) -> list[dict]:
        """Kelengkapan nilai per variabel terhadap periode yang dibutuhkan engine (CR v3.4 §4.2):
        bulan pertama..terakhir demand (lintas produk) + `horizon` bulan ke depan.

        Variabel per produk dihitung terisi bila ADA produk yang punya nilai di periode itu
        (indikasi kasar; kelengkapan per produk tetap diputuskan `usable_exog` saat forecast)."""
        expected = await self._expected_periods(horizon)
        filled_by_var = await self._repo.periods_by_variable()

        out = []
        for var in await self._repo.list():
            filled = filled_by_var.get(str(var.id), set())
            missing = [p for p in expected if p not in filled]
            out.append({
                "variable_id": str(var.id),
                "code": var.code,
                "first_period": min(filled) if filled else None,
                "last_period": max(filled) if filled else None,
                "n_expected": len(expected),
                "n_filled": len(expected) - len(missing),
                "missing_periods": missing,
            })
        return out

    async def exog_for_product(self, product_id) -> pd.DataFrame | None:
        """Matriks variabel AKTIF untuk satu produk (None bila tak ada)."""
        active = await self._repo.list_active()
        if not active:
            return None
        values = await self._repo.values_for([v.id for v in active], product_id)
        return build_exog(active, values)
