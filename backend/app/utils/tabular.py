"""
Pembaca tabel upload bersama (Fase 11.2b) — CSV (UTF-8) atau Excel (.xlsx/.xls).

Header dinormalisasi: trim + lowercase. Dipakai import variabel eksternal, stok ERP,
kedatangan material, dan pemakaian aktual. Gagal baca / kosong → UPLOAD_INVALID_FORMAT.
"""
import io
import re
from decimal import Decimal, InvalidOperation

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


# Penanda "tidak ada nilai" yang lazim di sheet Excel manual (CR v3.4 §4.3).
_EMPTY_MARKERS = {"", "-", "–", "—", "na", "n/a", "#n/a", "nan", "null"}
_CURRENCY = re.compile(r"^(rp\.?|idr)\s*", re.IGNORECASE)
_GROUPED = re.compile(r"^\d{1,3}([.,])\d{3}(\1\d{3})*$")  # 9,900 / 8.200 / 3,040,000
_MULTI_COMMA_GROUPS = re.compile(r"^\d{1,3}(,\d{3}){2,}(\.\d+)?$")  # 3,040,000 → pasti ribuan


def parse_decimal_id(raw) -> Decimal | None:
    """Angka dari sel tabel, toleran format Indonesia (CR v3.4 §4.3).

    - whitespace/tab di-trim (`"40,33\t"`)
    - koma = desimal; bila ada koma, titik dianggap pemisah ribuan (`"1.234,5"` → 1234.5).
      Tanpa koma, titik = desimal (`"27.2"`) — sel angka Excel asli tidak terpengaruh.
    - prefix `Rp`/`IDR` → rupiah bulat: pemisah ribuan `,` maupun `.` dibuang
      (`"Rp 9,900"`, `"Rp 8.200"` → 9900, 8200)
    - ≥ 2 grup ribuan berkoma tanpa prefix (`"3,040,000"`) → ribuan. Satu grup tanpa prefix
      (`"9,900"`) tetap dibaca koma desimal (9.9) — ambigu, jadi tulis `Rp` untuk harga.
    - akhiran `%` → pecahan (`"10%"` → 0.1)
    - kosong / `-` / `NA` / `#N/A` → None (sel dilewati, bukan error)
    Teks lain → ValueError.
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return Decimal(str(raw))
    text = str(raw).replace("\u00a0", " ").strip()
    if text.lower() in _EMPTY_MARKERS:
        return None
    percent = text.endswith("%")
    if percent:
        text = text[:-1].strip()
    currency = bool(_CURRENCY.match(text))
    text = _CURRENCY.sub("", text).replace(" ", "")
    if currency and _GROUPED.match(text):
        text = text.replace(",", "").replace(".", "")
    elif _MULTI_COMMA_GROUPS.match(text):
        text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"'{raw}' bukan angka valid.") from exc
    if not value.is_finite():
        raise ValueError(f"'{raw}' bukan angka valid.")
    return value / 100 if percent else value
