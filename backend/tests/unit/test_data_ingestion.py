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
