"""
Pembaca tabel upload bersama (Fase 11.2b) — CSV (UTF-8) atau Excel (.xlsx/.xls).

Header dinormalisasi: trim + lowercase. Dipakai import variabel eksternal, stok ERP,
kedatangan material, dan pemakaian aktual. Gagal baca / kosong → UPLOAD_INVALID_FORMAT.
"""
import io

import pandas as pd

from app.utils.exceptions import UploadInvalidFormatError

_EXCEL = (".xlsx", ".xls")


def read_table(filename: str, content: bytes) -> pd.DataFrame:
    name = (filename or "").lower()
    if not content:
        raise UploadInvalidFormatError("File kosong.")
    try:
        if name.endswith(_EXCEL):
            df = pd.read_excel(io.BytesIO(content))
        elif name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
        else:
            raise UploadInvalidFormatError("Format file harus .csv atau .xlsx.")
    except UploadInvalidFormatError:
        raise
    except Exception as exc:
        raise UploadInvalidFormatError(f"Gagal membaca file: {exc}") from exc
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def require_columns(df: pd.DataFrame, required: set[str]) -> None:
    missing = required - set(df.columns)
    if missing:
        raise UploadInvalidFormatError(f"Kolom wajib hilang: {', '.join(sorted(missing))}.")


def cell(raw) -> str:
    """Nilai sel sebagai string ter-trim; NaN/None → ''."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    text = str(raw).strip()
    return "" if text.lower() == "nan" else text
