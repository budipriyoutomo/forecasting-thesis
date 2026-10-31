"""
Fase 11.6/11.7 — export proyeksi stok & metrik inventory (xlsx/pdf). Repo di-mock.

Kolom pakai KODE material/produk (bukan UUID) supaya langsung bisa dipakai di
lampiran thesis; id tak dikenal → fallback ke id.
"""
import io
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from app.services.export_service import (
    ExportService,
    build_metrics_pdf,
    build_metrics_xlsx,
    build_stock_projection_pdf,
    build_stock_projection_xlsx,
)
from app.utils.exceptions import ForbiddenRoleError
from tests.unit.test_export_service import _async

USER = "u1"
LABELS = {"m1": "PRF-01", "p1": "Yoghurt ST"}


def _proj(mid="m1", scenario="proposed", period="2025-01-01", ending=80.0, shortage=0.0, within=True):
    return SimpleNamespace(
        material_id=mid, scenario=scenario, period=period, opening_qty=100.0, receipt_qty=0.0,
        usage_qty=20.0, order_qty=0.0, ending_qty=ending, shortage_qty=shortage,
        capacity_qty=200.0, utilization_opening_pct=50.0, utilization_ending_pct=40.0,
        is_within_capacity=within,
    )


def _metric(tt="material", tid="m1", scope="forecastiq"):
    return SimpleNamespace(
        target_type=tt, target_id=tid, scope=scope, service_level=0.95, fill_rate=0.98,
        stock_out_rate=0.05, inventory_turnover=4.2, inventory_days=7.1, shortage_cost=1500.0,
    )


def _headers(ws):
    return [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]


def test_build_stock_projection_xlsx_pakai_kode_material():
    content = build_stock_projection_xlsx([_proj(), _proj(scenario="baseline")], LABELS)

    ws = load_workbook(io.BytesIO(content)).active
    headers = _headers(ws)
    assert headers[:3] == ["material", "scenario", "period"]
    for col in ("ending_qty", "shortage_qty", "capacity_qty", "utilization_ending_pct", "is_within_capacity"):
        assert col in headers
    assert ws.cell(row=2, column=1).value == "PRF-01"
    assert ws.max_row == 3


def test_build_stock_projection_xlsx_id_tak_dikenal_fallback_id():
    ws = load_workbook(io.BytesIO(build_stock_projection_xlsx([_proj(mid="zz")], LABELS))).active
    assert ws.cell(row=2, column=1).value == "zz"


def test_build_stock_projection_pdf():
    content = build_stock_projection_pdf(
        SimpleNamespace(id="r1"), [_proj(), _proj(shortage=5.0, within=False)], LABELS
    )
    assert content[:4] == b"%PDF"


def test_build_metrics_xlsx():
    content = build_metrics_xlsx([_metric(), _metric(tt="product", tid="p1", scope="baseline")], LABELS)

    ws = load_workbook(io.BytesIO(content)).active
    headers = _headers(ws)
    assert headers[:3] == ["target_type", "target", "scope"]
    for col in ("service_level", "fill_rate", "stock_out_rate", "inventory_turnover", "inventory_days", "shortage_cost"):
        assert col in headers
    assert ws.cell(row=2, column=2).value == "PRF-01"
    assert ws.cell(row=3, column=2).value == "Yoghurt ST"


def test_build_metrics_xlsx_nilai_kosong_tetap_aman():
    m = _metric()
    m.inventory_days = None
    m.shortage_cost = None
    ws = load_workbook(io.BytesIO(build_metrics_xlsx([m], LABELS))).active
    col = _headers(ws).index("inventory_days") + 1
    assert ws.cell(row=2, column=col).value is None


def test_build_metrics_pdf():
    m = _metric()
    m.inventory_days = None
    assert build_metrics_pdf(SimpleNamespace(id="r1"), [m, _metric(tt="product", tid="p1")], LABELS)[:4] == b"%PDF"


def _svc(run_user=USER, projections=None, metrics=None):
    forecast_repo = SimpleNamespace(get_run=_async(SimpleNamespace(id="r1", user_id=run_user)))
    return ExportService(
        forecast_repo,
        SimpleNamespace(),
        storage=None,
        projections=SimpleNamespace(list_by_run=_async(projections or [])),
        metrics_repo=SimpleNamespace(list_by_run=_async(metrics or [])),
        materials=SimpleNamespace(list=_async([SimpleNamespace(id="m1", code="PRF-01")])),
        products=SimpleNamespace(list=_async([SimpleNamespace(id="p1", code="Yoghurt ST")])),
    )


@pytest.mark.asyncio
async def test_export_stock_projection_filter_skenario():
    svc = _svc(projections=[_proj(), _proj(scenario="baseline")])

    content, filename, _ = await svc.export_stock_projection(USER, "r1", "xlsx", scenario="proposed")

    ws = load_workbook(io.BytesIO(content)).active
    assert filename == "stock_projection_r1.xlsx"
    assert ws.max_row == 2
    assert ws.cell(row=2, column=1).value == "PRF-01"


@pytest.mark.asyncio
async def test_export_stock_projection_pdf():
    content, filename, mime = await _svc(projections=[_proj()]).export_stock_projection(USER, "r1", "pdf")
    assert content[:4] == b"%PDF" and filename.endswith(".pdf") and mime == "application/pdf"


@pytest.mark.asyncio
async def test_export_metrics_filter_target_type():
    svc = _svc(metrics=[_metric(), _metric(tt="product", tid="p1")])

    content, filename, _ = await svc.export_metrics(USER, "r1", "xlsx", target_type="material")

    ws = load_workbook(io.BytesIO(content)).active
    assert filename == "inventory_metrics_r1.xlsx"
    assert ws.max_row == 2


@pytest.mark.asyncio
async def test_export_planning_run_milik_user_lain_403():
    with pytest.raises(ForbiddenRoleError):
        await _svc(run_user="u2").export_stock_projection(USER, "r1", "xlsx")


# ── API ──

from app.api.deps import get_export_service  # noqa: E402
from app.main import app  # noqa: E402

USER_SUB = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def _api_svc():
    svc = _svc(run_user=USER_SUB, projections=[_proj()], metrics=[_metric()])
    app.dependency_overrides[get_export_service] = lambda: svc
    yield
    app.dependency_overrides.pop(get_export_service, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,magic",
    [
        ("/api/v1/forecast/runs/r1/stock-projection/export", b"PK"),
        ("/api/v1/forecast/runs/r1/stock-projection/export?format=pdf&scenario=proposed", b"%PDF"),
        ("/api/v1/forecast/runs/r1/inventory-metrics/export", b"PK"),
        ("/api/v1/forecast/runs/r1/inventory-metrics/export?format=pdf&target_type=material", b"%PDF"),
    ],
)
async def test_api_export_planning(client, auth_headers, _api_svc, path, magic):
    res = await client.get(path, headers=auth_headers)

    assert res.status_code == 200
    assert res.content[:len(magic)] == magic
    assert "attachment" in res.headers["content-disposition"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/forecast/runs/r1/stock-projection/export?format=csv",
        "/api/v1/forecast/runs/r1/stock-projection/export?scenario=lain",
        "/api/v1/forecast/runs/r1/inventory-metrics/export?target_type=gudang",
    ],
)
async def test_api_export_planning_param_invalid_422(client, auth_headers, _api_svc, path):
    assert (await client.get(path, headers=auth_headers)).status_code == 422


@pytest.mark.asyncio
async def test_api_export_planning_tanpa_token_401(client, _api_svc):
    assert (await client.get("/api/v1/forecast/runs/r1/stock-projection/export")).status_code == 401
