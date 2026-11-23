"""
CR v3.7 §5 (P1) — sheet "Format Thesis" di export forecast (`build_forecast_xlsx`).

Memakai output `build_method_comparison` yang sama dengan endpoint method-comparison; sheet
"Forecast" lama tidak berubah (kompatibilitas).
"""
import io
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openpyxl import load_workbook

from app.services.export_service import ExportService, build_forecast_xlsx
from app.services.forecasting.method_comparison import build_method_comparison
from app.services.forecasting.selection import DEFAULT_CRITERIA
from tests.unit.test_export_service import USER, _async, _fresult

DATES = ("2026-01-01", "2026-12-01")


def _cand(method, mad, mape, mfe, values=(10.4, 20.6)):
    return {
        "method": method, "mad": mad, "mape": mape, "mfe": mfe, "mse": 1.0,
        "forecast": [{"date": d, "value": v, "lower": v, "upper": v} for d, v in zip(DATES, values)],
    }


def _result(pid, cands, status="COMPLETED"):
    r = _fresult(pid)
    r.status = status
    r.candidates_evaluated = cands if status == "COMPLETED" else None
    r.method_used = "random_forest" if status == "COMPLETED" else None
    return r


RESULTS = [
    _result("p1", [_cand("random_forest", 2, 5, -1), _cand("lstm", 1, 4, 0)]),
    _result("p2", [_cand("random_forest", 4, 7, 1)]),
    _result("p3", [], status="INSUFFICIENT_DATA"),
]
LABELS = {"p1": "PL", "p2": "SB", "p3": "BB"}


def _cells(ws) -> list[list]:
    return [tuple(row) for row in ws.iter_rows(values_only=True)]


def _find(rows, value):
    return next(i for i, row in enumerate(rows) if row and row[0] == value)


def _thesis():
    content = build_forecast_xlsx(RESULTS, build_method_comparison(RESULTS, DEFAULT_CRITERIA), LABELS)
    wb = load_workbook(io.BytesIO(content))
    return wb, _cells(wb["Format Thesis"])


def test_dua_sheet_forecast_lama_tidak_berubah():
    wb, _ = _thesis()
    assert wb.sheetnames == ["Forecast", "Format Thesis"]
    ws = wb["Forecast"]
    assert ws.cell(row=1, column=1).value == "product_id"
    assert ws.max_row == 4  # header + 3 hasil


def test_blok_per_metode_urutan_thesis():
    _, rows = _thesis()
    titles = [row[0] for row in rows if row and isinstance(row[0], str) and ". Metode " in row[0]]
    assert titles == ["1. Metode Random Forest", "2. Metode LSTM"]


def test_tabel_hasil_ramalan_label_periode_dan_qty_bulat():
    _, rows = _thesis()
    head = _find(rows, "1. Metode Random Forest") + 2
    assert rows[head][:4] == ("Varian", "Jan-26", "Des-26", "Total")
    assert rows[head + 1][:4] == ("PL", 10, 21, 31)
    assert rows[head + 3][:4] == ("BB", "—", "—", "—")  # produk gagal


def test_tabel_pengujian_dengan_average_dan_catatan_n():
    _, rows = _thesis()
    start = _find(rows, "2. Metode LSTM")
    head = next(i for i in range(start, len(rows)) if rows[i][:4] == ("Varian", "MAD", "MAPE", "MFE"))
    avg = next(i for i in range(head, len(rows)) if rows[i][0] == "Average")
    assert rows[avg][1:4] == (1.0, 4.0, 0.0)
    assert rows[avg][4] == "n = 1 dari 3 varian"
    assert rows[head + 2][1] == "—"  # SB: LSTM gagal


def test_blok_analisis_metode_terbaik():
    _, rows = _thesis()
    start = _find(rows, "3. Analisis pemilihan metode terbaik")
    head = start + 1
    assert rows[head][:6] == ("Peringkat", "Metode", "Avg MAD", "Avg MAPE", "Avg MFE", "Varian")
    assert rows[head + 1][:2] == (1, "Random Forest")
    flat = [str(c) for row in rows[start:] for c in row if c is not None]
    assert any(c.startswith("Kesimpulan: Random Forest") for c in flat)
    assert any("Tidak dibandingkan" in c and "LSTM" in c for c in flat)  # ranking_basis common


def test_tanpa_comparison_tetap_satu_sheet():
    wb = load_workbook(io.BytesIO(build_forecast_xlsx([_fresult("p1")])))
    assert wb.sheetnames == ["Forecast"]


@pytest.mark.asyncio
async def test_export_forecast_menyertakan_format_thesis():
    forecast_repo = MagicMock()
    forecast_repo.get_run = _async(SimpleNamespace(id="r1", user_id=USER))
    forecast_repo.list_results = _async(RESULTS)
    products = SimpleNamespace(list=_async([SimpleNamespace(id="p1", code="PL")]))
    svc = ExportService(forecast_repo, MagicMock(), None, products=products)

    content, _, _ = await svc.export_forecast(USER, "r1")

    wb = load_workbook(io.BytesIO(content))
    rows = _cells(wb["Format Thesis"])
    head = _find(rows, "1. Metode Random Forest") + 2
    assert rows[head + 1][0] == "PL"
    assert rows[head + 2][0] == "p2"  # tanpa kode → fallback id (8 char)


@pytest.mark.asyncio
async def test_export_forecast_hasil_lama_tanpa_kandidat_tetap_jalan():
    forecast_repo = MagicMock()
    forecast_repo.get_run = _async(SimpleNamespace(id="r1", user_id=USER))
    forecast_repo.list_results = _async([_fresult("m1")])  # tanpa candidates_evaluated
    svc = ExportService(forecast_repo, MagicMock(), None)

    content, _, _ = await svc.export_forecast(USER, "r1")

    assert load_workbook(io.BytesIO(content)).sheetnames == ["Forecast", "Format Thesis"]
