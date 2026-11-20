"""Fase 3 v3.0 — parsing CSV demand produk (3 seri paralel)."""
from decimal import Decimal

import pytest

from app.services import data_ingestion_service as ing
from app.utils.exceptions import InsufficientDataError, UploadInvalidFormatError


def _csv(header: str, rows: list[str]) -> bytes:
    return ("\n".join([header, *rows])).encode("utf-8")


def test_extract_demand_rows_lengkap():
    content = _csv(
        "product_code,period,forecast_existing,planning,actual",
        ["SKU-1,2026-01-01,90,95,100", "SKU-1,2026-02-01,,,110"],
    )
    rows = ing.extract_demand_rows(content)
    assert len(rows) == 2
    assert rows[0]["forecast_existing"] == Decimal("90")
    assert rows[0]["actual"] == Decimal("100")
    # kolom opsional kosong → None, actual tetap terisi
    assert rows[1]["forecast_existing"] is None
    assert rows[1]["planning"] is None
    assert rows[1]["actual"] == Decimal("110")


def test_period_alias_date_diterima():
    content = _csv("product_code,date,actual", ["SKU-1,2026-03-01,50"])
    rows = ing.extract_demand_rows(content)
    assert rows[0]["period"].isoformat() == "2026-03-01"


def test_extract_demand_rows_normalisasi_periode():
    """CR v3.4 §4.1 — tanggal 24 (format Excel thesis) disimpan sebagai awal bulan."""
    content = _csv("product_code,period,actual", ["SKU-1,2024-01-24,100", "SKU-1,2024-02-29,110"])
    rows = ing.extract_demand_rows(content)
    assert [r["period"].isoformat() for r in rows] == ["2024-01-01", "2024-02-01"]


def test_baris_actual_invalid_di_skip():
    content = _csv(
        "product_code,period,actual",
        ["SKU-1,2026-01-01,abc", "SKU-1,2026-02-01,120"],
    )
    rows = ing.extract_demand_rows(content)
    assert [str(r["actual"]) for r in rows] == ["120"]


def test_validate_kolom_actual_hilang():
    content = _csv("product_code,period", [f"SKU-1,2026-01-{i:02d}" for i in range(1, 13)])
    with pytest.raises(UploadInvalidFormatError, match="actual"):
        ing.parse_and_validate_csv("f.csv", content)


def test_validate_n_products_detected():
    content = _csv(
        "product_code,period,actual",
        [f"SKU-{i % 2},2026-01-{(i % 28) + 1:02d},{10 + i}" for i in range(12)],
    )
    summary = ing.parse_and_validate_csv("f.csv", content)
    assert summary["n_products_detected"] == 2
    assert summary["n_rows"] == 12


def test_validate_insufficient_rows():
    content = _csv("product_code,period,actual", ["SKU-1,2026-01-01,10"])
    with pytest.raises(InsufficientDataError):
        ing.parse_and_validate_csv("f.csv", content)


# ── CR v3.4 §4.1 — normalisasi periode demand tidak boleh diam-diam ──


def test_extract_demand_rows_simpan_tanggal_asli():
    rows = ing.extract_demand_rows(_csv("product_code,period,actual", ["SKU-1,2024-01-24,100"]))
    assert rows[0]["period_original"].isoformat() == "2024-01-24"


def test_demand_period_warnings_normalisasi_dan_bulan_ganda():
    content = _csv(
        "product_code,period,actual",
        ["SKU-1,2024-01-24,100", "SKU-1,2024-02-01,90", "SKU-1,2024-01-25,80", "SKU-2,2024-01-01,5"],
    )
    warnings = ing.demand_period_warnings(ing.extract_demand_rows(content))
    assert warnings == [
        "2 baris: periode digeser ke awal bulan (mis. 2024-01-24 → 2024-01-01).",
        (
            "1 produk-bulan punya lebih dari satu tanggal (mis. SKU-1 2024-01: 2024-01-24, 2024-01-25) — "
            "nilainya dijumlahkan saat forecast. Cek format tanggal: 'Jan-24' bisa terbaca 24-Jan tahun berjalan."
        ),
    ]


def test_demand_period_warnings_data_rapi_kosong():
    content = _csv("product_code,period,actual", ["SKU-1,2024-01-01,100", "SKU-1,2024-02-01,90"])
    assert ing.demand_period_warnings(ing.extract_demand_rows(content)) == []
