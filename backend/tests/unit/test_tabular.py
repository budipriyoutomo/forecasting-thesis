"""Fase 11.2b — util baca tabel upload (CSV / Excel) bersama untuk import master/transaksi."""
import io
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from app.utils.exceptions import UploadInvalidFormatError
from app.utils.tabular import parse_decimal_id, parse_iso_date, read_table


def test_csv_header_dinormalisasi():
    df = read_table("x.csv", b" Variable_Code ,Period,Value\nsuhu,2026-01-01,30\n")
    assert list(df.columns) == ["variable_code", "period", "value"]
    assert df.iloc[0]["value"] == 30


def test_csv_pemisah_titik_koma_excel_indonesia():
    # Excel locale Indonesia menyimpan "CSV" dengan pemisah ';' — dulu jadi satu kolom
    # lalu ditolak "Kolom wajib hilang" yang membingungkan.
    df = read_table("x.csv", b"material_code;qty\nCAP;1,5\n")
    assert list(df.columns) == ["material_code", "qty"]
    assert df.iloc[0]["material_code"] == "CAP"


def test_csv_baris_kosong_di_ekor_dibuang():
    df = read_table("x.csv", b"a,b\n1,2\n,\n,\n")
    assert len(df) == 1


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-10-01", date(2026, 10, 1)),
        ("2026-10-01 00:00:00", date(2026, 10, 1)),  # sel tanggal Excel → Timestamp → str
        (pd.Timestamp("2026-10-01"), date(2026, 10, 1)),
        ("", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_parse_iso_date(raw, expected):
    assert parse_iso_date(raw) == expected


@pytest.mark.parametrize("raw", ["05/10/2026", "Oct-2026", "besok", "2026-13-01"])
def test_parse_iso_date_tidak_valid(raw):
    with pytest.raises(ValueError):
        parse_iso_date(raw)


def test_excel():
    buf = io.BytesIO()
    pd.DataFrame({"Code": ["a"], "Qty": [5]}).to_excel(buf, index=False)
    df = read_table("data.xlsx", buf.getvalue())
    assert list(df.columns) == ["code", "qty"]
    assert df.iloc[0]["qty"] == 5


@pytest.mark.parametrize("name,content", [("a.pdf", b"x"), ("a.csv", b""), ("a.xlsx", b"bukan excel")])
def test_tidak_valid(name, content):
    with pytest.raises(UploadInvalidFormatError):
        read_table(name, content)


def test_require_columns():
    from app.utils.tabular import require_columns

    df = read_table("x.csv", b"a,b\n1,2\n")
    require_columns(df, {"a"})
    with pytest.raises(UploadInvalidFormatError, match="c"):
        require_columns(df, {"a", "c"})


# ── CR v3.4 §4.3 — parser angka toleran (format Excel thesis) ──

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("40,33\t", Decimal("40.33")),  # koma desimal + tab (sel AS Excel thesis)
        ("27.2", Decimal("27.2")),
        (27.2, Decimal("27.2")),
        (8200, Decimal("8200")),
        (" 1.234,5 ", Decimal("1234.5")),  # titik ribuan bila ada koma desimal
        ("10%", Decimal("0.1")),
        ("12,5 %", Decimal("0.125")),
        ("Rp 9,900", Decimal("9900")),  # harga di Excel thesis: prefix Rp + ribuan format Inggris
        ("Rp 8.200", Decimal("8200")),  # ribuan format Indonesia
        ("Rp 3,040,000", Decimal("3040000")),
        ("3,040,000", Decimal("3040000")),  # ≥ 2 grup ribuan → pasti ribuan, bukan desimal
        ("9,900", Decimal("9.9")),  # 1 grup tanpa Rp → tetap koma desimal (aturan Indonesia)
    ],
)
def test_parse_decimal_id(raw, expected):
    assert parse_decimal_id(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "  ", "-", "–", "NA", "n/a", "#N/A", float("nan")])
def test_parse_decimal_id_kosong_dilewati(raw):
    assert parse_decimal_id(raw) is None


@pytest.mark.parametrize("raw", ["abc", "Hujan", "1,2,3"])
def test_parse_decimal_id_tidak_valid(raw):
    with pytest.raises(ValueError):
        parse_decimal_id(raw)
