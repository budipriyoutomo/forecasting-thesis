"""
Data Ingestion Service — parsing & validasi CSV upload konsumsi raw material.

Ini adalah implementasi GREEN minimum untuk lulus tests/unit/test_upload.py
(lihat AGENTS.md §3 — TDD workflow). Persistensi ke database (upload_sessions,
consumption_history) dan penyimpanan ke Cloudflare R2 (temp/permanent) adalah
bagian dari Fase 3 penuh (docs/TASK_BREAKDOWN.md) — BELUM diimplementasikan
di sini. Fungsi ini murni parsing + validasi in-memory, sengaja dibuat kecil
agar siklus TDD contoh mudah diikuti dan direplikasi untuk service lain.

Kolom wajib CSV: material_code, date, quantity
"""
import io
import uuid
from datetime import date as date_type
from decimal import Decimal, InvalidOperation

import pandas as pd

from app.config import get_settings
from app.utils.exceptions import InsufficientDataError, UploadInvalidFormatError

REQUIRED_COLUMNS = {"material_code", "date", "quantity"}


def _normalized_df(content: bytes) -> pd.DataFrame:
    """Baca CSV dan normalisasi nama kolom (strip + lowercase)."""
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise UploadInvalidFormatError(f"Gagal membaca isi CSV: {exc}") from exc
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def extract_consumption_rows(content: bytes) -> list[dict]:
    """Ambil baris konsumsi ternormalisasi untuk disimpan ke consumption_history.

    Baris dengan tanggal/quantity tidak valid di-skip (sudah divalidasi ringkas
    di `parse_and_validate_csv`; di sini fokus ke baris yang benar-benar bisa
    disimpan). Mengembalikan list of {material_code, date, quantity}.
    """
    df = _normalized_df(content)
    rows: list[dict] = []
    for _, raw in df.iterrows():
        code = str(raw.get("material_code", "")).strip()
        if not code or code.lower() == "nan":
            continue
        try:
            parsed_date = pd.to_datetime(raw.get("date")).date()
        except (ValueError, TypeError):
            continue
        try:
            qty = Decimal(str(raw.get("quantity")))
        except (InvalidOperation, ValueError, TypeError):
            continue
        if not isinstance(parsed_date, date_type):
            continue
        rows.append({"material_code": code, "date": parsed_date, "quantity": qty})
    return rows


def parse_and_validate_csv(filename: str, content: bytes) -> dict:
    """
    Parse file CSV mentah, validasi struktur & isi minimal, dan kembalikan
    ringkasan yang siap dipakai endpoint upload.

    Raises:
        UploadInvalidFormatError: bukan CSV, kolom wajib hilang, atau file
            tidak bisa diparse sama sekali.
        InsufficientDataError: jumlah baris di bawah UPLOAD_MIN_ROWS.
    """
    settings = get_settings()

    if not filename.lower().endswith(".csv"):
        raise UploadInvalidFormatError(f"File '{filename}' bukan format CSV")

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:  # pandas bisa lempar berbagai jenis error parsing
        raise UploadInvalidFormatError(f"Gagal membaca isi CSV: {exc}") from exc

    missing_columns = REQUIRED_COLUMNS - set(df.columns.str.strip().str.lower())
    if missing_columns:
        raise UploadInvalidFormatError(
            f"Kolom wajib hilang: {', '.join(sorted(missing_columns))}"
        )

    n_rows = len(df)
    if n_rows < settings.UPLOAD_MIN_ROWS:
        raise InsufficientDataError(
            f"Data hanya {n_rows} baris, minimum {settings.UPLOAD_MIN_ROWS} baris diperlukan"
        )

    warnings: list[str] = []
    if df["quantity"].isna().any():
        warnings.append("Terdapat nilai quantity yang kosong pada beberapa baris")

    n_materials_detected = df["material_code"].nunique(dropna=True)

    return {
        "session_id": str(uuid.uuid4()),
        "n_rows": n_rows,
        "n_materials_detected": int(n_materials_detected),
        "preview": df.head(5).fillna("").to_dict(orient="records"),
        "warnings": warnings,
        "status": "validated",
    }
