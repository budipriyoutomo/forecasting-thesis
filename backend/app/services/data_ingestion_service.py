"""
Data Ingestion Service (v3.0) — parsing & validasi CSV demand produk jadi.

Menggantikan jalur konsumsi raw material v2.0. Struktur 3 seri paralel mengikuti
`Simulasi Thesis.xlsx` sheet "Bab I Plan vs Forecast":

  Kolom wajib : product_code, period, actual
  Kolom opsional: forecast_existing, planning

`period` menerima juga alias `date` (fleksibilitas file lama). `actual` adalah
realisasi produksi/penjualan — target/label untuk training model ML.
"""
import io
import uuid
from datetime import date as date_type
from decimal import Decimal, InvalidOperation

import pandas as pd

from app.config import get_settings
from app.utils.exceptions import InsufficientDataError, UploadInvalidFormatError

REQUIRED_COLUMNS = {"product_code", "period", "actual"}
_PERIOD_ALIASES = ("period", "date")


def _normalized_df(content: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise UploadInvalidFormatError(f"Gagal membaca isi CSV: {exc}") from exc
    df.columns = [str(c).strip().lower() for c in df.columns]
    # Normalisasi kolom waktu: terima `date` sebagai alias `period`.
    if "period" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "period"})
    return df


def _num(value) -> Decimal | None:
    raw = str(value).strip()
    if raw == "" or raw.lower() == "nan":
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def extract_demand_rows(content: bytes) -> list[dict]:
    """Ambil baris demand ternormalisasi untuk disimpan ke demand_history.

    Baris tanpa product_code / period valid / actual valid di-skip.
    Mengembalikan {product_code, period, forecast_existing, planning, actual}.
    """
    df = _normalized_df(content)
    rows: list[dict] = []
    for _, raw in df.iterrows():
        code = str(raw.get("product_code", "")).strip()
        if not code or code.lower() == "nan":
            continue
        try:
            period = pd.to_datetime(raw.get("period")).date()
        except (ValueError, TypeError):
            continue
        actual = _num(raw.get("actual"))
        if not isinstance(period, date_type) or actual is None:
            continue
        rows.append(
            {
                "product_code": code,
                "period": period,
                "forecast_existing": _num(raw.get("forecast_existing")),
                "planning": _num(raw.get("planning")),
                "actual": actual,
            }
        )
    return rows


def parse_and_validate_csv(filename: str, content: bytes) -> dict:
    """
    Parse CSV demand mentah, validasi struktur & isi minimal, kembalikan ringkasan
    untuk endpoint upload.

    Raises:
        UploadInvalidFormatError: bukan CSV / kolom wajib hilang / gagal parse.
        InsufficientDataError: jumlah baris di bawah UPLOAD_MIN_ROWS.
    """
    settings = get_settings()

    if not filename.lower().endswith(".csv"):
        raise UploadInvalidFormatError(f"File '{filename}' bukan format CSV")

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise UploadInvalidFormatError(f"Gagal membaca isi CSV: {exc}") from exc

    columns = set(df.columns.str.strip().str.lower())
    if "period" not in columns and "date" in columns:
        columns.add("period")
    missing_columns = REQUIRED_COLUMNS - columns
    if missing_columns:
        raise UploadInvalidFormatError(f"Kolom wajib hilang: {', '.join(sorted(missing_columns))}")

    n_rows = len(df)
    if n_rows < settings.UPLOAD_MIN_ROWS:
        raise InsufficientDataError(
            f"Data hanya {n_rows} baris, minimum {settings.UPLOAD_MIN_ROWS} baris diperlukan"
        )

    warnings: list[str] = []
    if df["actual"].isna().any():
        warnings.append("Terdapat nilai actual yang kosong pada beberapa baris")

    n_products_detected = df["product_code"].nunique(dropna=True)

    return {
        "session_id": str(uuid.uuid4()),
        "n_rows": n_rows,
        "n_products_detected": int(n_products_detected),
        "preview": df.head(5).fillna("").to_dict(orient="records"),
        "warnings": warnings,
        "status": "validated",
    }
