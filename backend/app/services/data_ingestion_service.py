"""
Data Ingestion Service (v3.0) — parsing & validasi CSV demand produk jadi.

Menggantikan jalur konsumsi raw material v2.0. Struktur 3 seri paralel mengikuti
`Simulasi Thesis.xlsx` sheet "Bab I Plan vs Forecast":

  Kolom wajib : product_code, period, actual
  Kolom opsional: forecast_existing, planning

`period` menerima juga alias `date` (fleksibilitas file lama). `actual` adalah
realisasi produksi/penjualan — target/label untuk training model ML.
"""
import re
import uuid
from datetime import date
from decimal import Decimal

import pandas as pd

from app.config import get_settings
from app.services.forecasting.preprocessing import normalize_period
from app.utils.exceptions import InsufficientDataError, UploadInvalidFormatError
from app.utils.tabular import cell, is_blank_row, parse_decimal_id, read_table, require_columns

REQUIRED_COLUMNS = {"product_code", "period", "actual"}
_OPTIONAL_NUMBERS = ("forecast_existing", "planning")
_MAX_VALUE = Decimal(10) ** 14  # Numeric(18, 4) — di atas ini INSERT gagal (dulu 500)
# dd/mm/yyyy vs mm/dd/yyyy tidak bisa dibedakan (05/10 = 5 Okt atau 10 Mei?) — pandas
# diam-diam memilih bulan-dulu. Ditolak; format bulan lain (Jan-24, 2024-01-24) tetap diterima.
_AMBIGUOUS_DATE = re.compile(r"^\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}$")


def _table(content: bytes) -> pd.DataFrame:
    # CSV via pembaca bersama: BOM UTF-8, pemisah ';' (Excel Indonesia), baris kosong di ekor.
    df = read_table("upload.csv", content, as_text=True)
    if "period" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "period"})  # alias file lama
    require_columns(df, REQUIRED_COLUMNS)
    return df


def _number(raw, name: str, line: int) -> Decimal | None:
    try:
        value = parse_decimal_id(raw)  # desimal titik atau koma
    except ValueError as exc:
        raise UploadInvalidFormatError(f"Baris {line}: '{name}' bukan angka valid.") from exc
    if value is None:
        return None
    if value < 0:
        raise UploadInvalidFormatError(f"Baris {line}: '{name}' tidak boleh negatif.")
    if value >= _MAX_VALUE:
        raise UploadInvalidFormatError(f"Baris {line}: '{name}' terlalu besar.")
    return value


def _period(raw, line: int) -> date:
    text = cell(raw)
    if text == "":
        raise UploadInvalidFormatError(f"Baris {line}: 'period' wajib diisi (format YYYY-MM-DD).")
    if _AMBIGUOUS_DATE.match(text):
        raise UploadInvalidFormatError(
            f"Baris {line}: 'period' '{text}' ambigu (hari/bulan) — tulis dengan format YYYY-MM-DD."
        )
    try:
        parsed = pd.to_datetime(text)
    except (ValueError, TypeError, OverflowError) as exc:
        raise UploadInvalidFormatError(f"Baris {line}: 'period' bukan tanggal valid (format YYYY-MM-DD).") from exc
    if pd.isna(parsed):
        raise UploadInvalidFormatError(f"Baris {line}: 'period' bukan tanggal valid (format YYYY-MM-DD).")
    return parsed.date()


def _parse(content: bytes) -> tuple[list[dict], list[int], list[dict], list[tuple]]:
    """→ (baris valid, nomor baris ber-actual kosong yang dilewati, preview mentah,
    duplikat (baris, baris pertama, kode, tanggal)).

    Satu baris rusak menolak seluruh file dengan nomor barisnya (sama seperti importer stok /
    pemakaian). Dulu baris rusak dibuang diam-diam: upload "sukses" tapi data hilang.
    Baris kosong total dilewati; `actual` kosong dilewati dan dilaporkan sebagai warning.
    """
    df = _table(content)
    rows: list[dict] = []
    empty_actual: list[int] = []
    preview: list[dict] = []
    seen: dict[tuple, int] = {}
    duplicates: list[tuple] = []
    for line, raw in enumerate(df.to_dict("records"), start=2):
        if is_blank_row(raw):
            continue
        if len(preview) < 5:
            preview.append({k: cell(v) for k, v in raw.items()})
        code = cell(raw.get("product_code"))
        if code == "":
            raise UploadInvalidFormatError(f"Baris {line}: 'product_code' wajib diisi.")
        original = _period(raw.get("period"), line)
        optional = {name: _number(raw.get(name), name, line) for name in _OPTIONAL_NUMBERS}
        actual = _number(raw.get("actual"), "actual", line)
        if actual is None:
            empty_actual.append(line)
            continue
        key = (code, original)
        if key in seen:
            duplicates.append((line, seen[key], code, original))
        else:
            seen[key] = line
        rows.append(
            {
                "product_code": code,
                "period": normalize_period(original),
                "period_original": original,
                **optional,
                "actual": actual,
            }
        )
    return rows, empty_actual, preview, duplicates


def extract_demand_rows(content: bytes) -> list[dict]:
    """Baris demand ternormalisasi untuk demand_history:
    {product_code, period, period_original, forecast_existing, planning, actual}."""
    return _parse(content)[0]


def parse_and_validate_csv(filename: str, content: bytes) -> dict:
    """
    Parse + validasi CSV demand, kembalikan ringkasan untuk endpoint upload.

    Raises:
        UploadInvalidFormatError: bukan CSV / kolom wajib hilang / baris tidak valid.
        InsufficientDataError: baris valid di bawah UPLOAD_MIN_ROWS.
    """
    settings = get_settings()
    if not (filename or "").lower().endswith(".csv"):
        raise UploadInvalidFormatError(f"File '{filename}' bukan format CSV")

    rows, empty_actual, preview, duplicates = _parse(content)
    n_rows = len(rows)
    if n_rows < settings.UPLOAD_MIN_ROWS:
        raise InsufficientDataError(
            f"Data valid hanya {n_rows} baris, minimum {settings.UPLOAD_MIN_ROWS} baris diperlukan"
        )

    warnings: list[str] = []
    if empty_actual:
        shown = ", ".join(str(n) for n in empty_actual[:10]) + ("…" if len(empty_actual) > 10 else "")
        warnings.append(f"{len(empty_actual)} baris dengan 'actual' kosong dilewati (baris {shown}).")
    if duplicates:
        line, first, code, period = duplicates[0]
        warnings.append(
            f"{len(duplicates)} baris punya produk + tanggal yang sama dengan baris lain "
            f"(mis. baris {line} = baris {first}: {code} {period}) — nilainya dijumlahkan saat forecast. "
            "Hapus bila tidak disengaja (mis. file terunggah dua kali)."
        )

    return {
        "session_id": str(uuid.uuid4()),
        "n_rows": n_rows,
        "n_products_detected": len({r["product_code"] for r in rows}),
        "preview": preview,
        "warnings": warnings,
        "status": "validated",
    }


def demand_period_warnings(rows: list[dict]) -> list[str]:
    """CR v3.4 §4.1 — laporkan normalisasi periode demand (tidak diam-diam):
    baris yang digeser ke awal bulan, dan produk-bulan dengan lebih dari satu tanggal asli
    (dijumlahkan saat forecast — sering tanda 'Jan-24' terbaca 24-Jan tahun berjalan)."""
    warnings = []
    shifted = [r for r in rows if r["period_original"] != r["period"]]
    if shifted:
        ex = shifted[0]
        warnings.append(
            f"{len(shifted)} baris: periode digeser ke awal bulan "
            f"(mis. {ex['period_original']} → {ex['period']})."
        )
    dates: dict[tuple, set] = {}
    for r in rows:
        dates.setdefault((r["product_code"], r["period"]), set()).add(r["period_original"])
    multi = [(key, sorted(d)) for key, d in dates.items() if len(d) > 1]
    if multi:
        (code, period), ds = multi[0]
        warnings.append(
            f"{len(multi)} produk-bulan punya lebih dari satu tanggal (mis. {code} {period:%Y-%m}: "
            f"{', '.join(str(d) for d in ds)}) — nilainya dijumlahkan saat forecast. Cek format tanggal: "
            "'Jan-24' bisa terbaca 24-Jan tahun berjalan."
        )
    return warnings
