"""
Fase 7 — DashboardService (agregasi ringkasan). Repo di-mock.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.dashboard_service import DashboardService

USER = "u1"


class FakeMaterials:
    def __init__(self, n):
        self._items = [SimpleNamespace(id=f"m{i}") for i in range(n)]

    async def list(self):
        return self._items


class FakeForecast:
    def __init__(self, run, results):
        self._run = run
        self._results = results

    async def get_latest_run(self):
        return self._run

    async def list_runs(self, limit=50):
        # CR v3.6 §1 — dashboard membaca pembuat run lewat list_runs(1)
        return [(self._run, getattr(self._run, "created_by", None))] if self._run else []

    async def list_results(self, run_id):
        return self._results


class FakeReorder:
    def __init__(self, recs):
        self._recs = recs

    async def list_by_run(self, run_id):
        return self._recs


class FakeOverride:
    def __init__(self, recent):
        self._recent = recent

    async def list_recent(self, limit=20):
        return self._recent[:limit]


class FakeWarehouseVal:
    def __init__(self, v):
        self._v = v

    async def get_for_run(self, run_id):
        return self._v


class FakeInvMetrics:
    def __init__(self, rows):
        self._rows = rows

    async def list_by_run(self, run_id):
        return self._rows


def _result(status="COMPLETED", mase=None, mape=None, mad=None, mfe=None):
    return SimpleNamespace(
        status=status,
        mase=Decimal(str(mase)) if mase is not None else None,
        mape=Decimal(str(mape)) if mape is not None else None,
        mad=Decimal(str(mad)) if mad is not None else None,
        mfe=Decimal(str(mfe)) if mfe is not None else None,
    )


def _rec(status):
    return SimpleNamespace(status=status)


@pytest.mark.asyncio
async def test_summary_dengan_run_terbaru():
    run = SimpleNamespace(id="r1", status="COMPLETED")
    svc = DashboardService(
        FakeMaterials(3),
        FakeForecast(run, [_result(mase=0.4), _result(mase=0.6), _result(status="INSUFFICIENT_DATA")]),
        FakeReorder([_rec("urgent"), _rec("urgent"), _rec("safe")]),
        FakeOverride([object(), object()]),
    )

    summary = await svc.summary(USER)

    assert summary["n_materials"] == 3
    assert summary["latest_run"]["n_completed"] == 2
    # CR v3.5 §4: forecast_results per PRODUK — bukan material.
    assert summary["latest_run"]["n_products"] == 3
    assert "n_materials" not in summary["latest_run"]
    assert summary["latest_run"]["n_failed"] == 1
    assert summary["latest_run"]["avg_mase"] == pytest.approx(0.5)
    assert summary["reorder_status_counts"] == {"urgent": 2, "safe": 1, "overstock": 0}
    assert summary["n_recent_overrides"] == 2


@pytest.mark.asyncio
async def test_summary_widget_v3_tic_warehouse_metrics():
    # Fase 9: dashboard diperluas — TIC run, indikator kapasitas gudang, metrik inventory per scope.
    run = SimpleNamespace(id="r1", status="COMPLETED")
    recs = [
        SimpleNamespace(status="urgent", total_inventory_cost=Decimal("120")),
        SimpleNamespace(status="safe", total_inventory_cost=Decimal("80")),
    ]
    wval = SimpleNamespace(
        is_within_capacity=True,
        details=[
            {"product_id": "p1", "required_qty": 80, "capacity_qty": 100, "is_within_capacity": True},
            {"product_id": "p2", "required_qty": 40, "capacity_qty": 50, "is_within_capacity": True},
        ],
    )
    metrics = [
        SimpleNamespace(scope="baseline", service_level=Decimal("0.90"), fill_rate=Decimal("0.95"),
                        stock_out_rate=Decimal("0.10"), inventory_turnover=Decimal("4")),
        SimpleNamespace(scope="forecastiq", service_level=Decimal("0.98"), fill_rate=Decimal("0.99"),
                        stock_out_rate=Decimal("0.02"), inventory_turnover=Decimal("5")),
    ]
    svc = DashboardService(
        FakeMaterials(2),
        FakeForecast(run, [_result(mase=0.4, mape=5.0)]),
        FakeReorder(recs),
        FakeOverride([]),
        warehouse_repo=FakeWarehouseVal(wval),
        inventory_metrics_repo=FakeInvMetrics(metrics),
    )

    s = await svc.summary(USER)

    assert s["latest_run"]["total_inventory_cost"] == pytest.approx(200)
    assert s["latest_run"]["avg_mape"] == pytest.approx(5.0)
    assert s["warehouse"]["is_within_capacity"] is True
    assert s["warehouse"]["n_products_over"] == 0
    assert s["warehouse"]["n_products_checked"] == 2
    assert s["inventory_metrics"]["forecastiq"]["service_level"] == pytest.approx(0.98)
    assert s["inventory_metrics"]["baseline"]["fill_rate"] == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_summary_tanpa_repo_baru_tetap_jalan():
    # backward compat: tanpa warehouse/metrics repo → field None, tidak error.
    run = SimpleNamespace(id="r1", status="COMPLETED")
    svc = DashboardService(FakeMaterials(1), FakeForecast(run, [_result(mase=0.4)]), FakeReorder([]), FakeOverride([]))
    s = await svc.summary(USER)
    assert s["warehouse"] is None
    assert s["inventory_metrics"] is None


@pytest.mark.asyncio
async def test_summary_tanpa_run():
    svc = DashboardService(FakeMaterials(0), FakeForecast(None, []), FakeReorder([]), FakeOverride([]))

    summary = await svc.summary(USER)

    assert summary["n_materials"] == 0
    assert summary["latest_run"] is None
    assert summary["reorder_status_counts"] == {"urgent": 0, "safe": 0, "overstock": 0}


@pytest.mark.asyncio
async def test_summary_run_tanpa_mase_avg_none():
    run = SimpleNamespace(id="r1", status="COMPLETED")
    svc = DashboardService(
        FakeMaterials(1),
        FakeForecast(run, [_result(status="INSUFFICIENT_DATA")]),
        FakeReorder([]),
        FakeOverride([]),
    )

    summary = await svc.summary(USER)

    assert summary["latest_run"]["avg_mase"] is None



# ── CR v3.6 §1/§3 — field additive dashboard ──
class FakeProducts:
    def __init__(self, products):
        self._by_id = {p.id: p for p in products}

    async def get_by_id(self, pid):
        return self._by_id.get(pid)


class FakeProjections:
    def __init__(self, rows):
        self._rows = rows

    async def list_by_run(self, run_id):
        return self._rows


class FakeCost:
    def __init__(self, summary=None, error=None):
        self._summary = summary
        self._error = error

    async def get_cost_summary(self, user_id, run_id):
        if self._error:
            raise self._error
        return self._summary


@pytest.mark.asyncio
async def test_latest_run_membawa_pembuat_tanggal_dan_pending():
    from datetime import datetime, timezone

    run = SimpleNamespace(
        id="r1", status="COMPLETED", created_at=datetime(2026, 11, 20, tzinfo=timezone.utc), created_by="PPIC A"
    )
    pending = SimpleNamespace(status="COMPLETED", mase=None, mape=None, selection_status="PENDING_SELECTION")
    svc = DashboardService(
        FakeMaterials(1), FakeForecast(run, [_result(mase=0.5), pending]), FakeReorder([]), FakeOverride([])
    )

    s = await svc.summary(USER)

    assert s["latest_run"]["created_at"] == "2026-11-20T00:00:00+00:00"
    assert s["latest_run"]["created_by"] == "PPIC A"
    assert s["latest_run"]["n_pending_selection"] == 1


@pytest.mark.asyncio
async def test_latest_run_baseline_dan_savings_dari_cost_service():
    run = SimpleNamespace(id="r1", status="COMPLETED")
    recs = [SimpleNamespace(status="safe", total_inventory_cost=Decimal("80"))]
    cost = SimpleNamespace(baseline_inventory_cost=Decimal("100"), savings_pct=Decimal("20"))
    svc = DashboardService(
        FakeMaterials(1), FakeForecast(run, [_result()]), FakeReorder(recs), FakeOverride([]),
        cost_service=FakeCost(cost),
    )

    s = await svc.summary(USER)

    assert s["latest_run"]["total_inventory_cost_baseline"] == pytest.approx(100)
    assert s["latest_run"]["savings_pct"] == pytest.approx(20)


@pytest.mark.asyncio
async def test_baseline_gagal_dihitung_tidak_memutus_dashboard():
    from app.utils.exceptions import BomNotFoundError

    run = SimpleNamespace(id="r1", status="COMPLETED")
    recs = [SimpleNamespace(status="safe", total_inventory_cost=Decimal("80"))]
    svc = DashboardService(
        FakeMaterials(1), FakeForecast(run, [_result()]), FakeReorder(recs), FakeOverride([]),
        cost_service=FakeCost(error=BomNotFoundError("x")),
    )

    s = await svc.summary(USER)

    assert s["latest_run"]["total_inventory_cost_baseline"] is None
    assert s["latest_run"]["savings_pct"] is None


@pytest.mark.asyncio
async def test_baseline_tidak_dihitung_tanpa_reorder():
    run = SimpleNamespace(id="r1", status="COMPLETED")
    cost = SimpleNamespace(baseline_inventory_cost=Decimal("100"), savings_pct=Decimal("20"))
    svc = DashboardService(
        FakeMaterials(1), FakeForecast(run, [_result()]), FakeReorder([]), FakeOverride([]),
        cost_service=FakeCost(cost),
    )

    s = await svc.summary(USER)

    assert s["latest_run"]["total_inventory_cost_baseline"] is None


@pytest.mark.asyncio
async def test_warehouse_products_over_urut_kelebihan_maks_10():
    run = SimpleNamespace(id="r1", status="COMPLETED")
    details = [
        {"product_id": f"p{i}", "required_qty": 100 + i, "capacity_qty": 100, "is_within_capacity": False}
        for i in range(1, 13)
    ] + [{"product_id": "ok", "required_qty": 10, "capacity_qty": 100, "is_within_capacity": True}]
    products = [SimpleNamespace(id=f"p{i}", code=f"SKU-{i}", name=f"Produk {i}") for i in range(1, 13)]
    svc = DashboardService(
        FakeMaterials(1), FakeForecast(run, [_result()]), FakeReorder([]), FakeOverride([]),
        warehouse_repo=FakeWarehouseVal(SimpleNamespace(is_within_capacity=False, details=details)),
        products=FakeProducts(products),
    )

    s = await svc.summary(USER)

    over = s["warehouse"]["products_over"]
    assert len(over) == 10
    assert over[0] == {"product_id": "p12", "code": "SKU-12", "name": "Produk 12", "excess_qty": pytest.approx(12)}
    assert s["warehouse"]["n_products_over"] == 12


@pytest.mark.asyncio
async def test_attention_gagal_data_biaya_dan_kekurangan():
    run = SimpleNamespace(id="r1", status="COMPLETED")
    recs = [
        SimpleNamespace(status="urgent", item_status="MISSING_UNIT_PRICE", total_inventory_cost=None),
        SimpleNamespace(status="safe", item_status="MISSING_HOLDING_RATE", total_inventory_cost=None),
        SimpleNamespace(status="safe", item_status="COMPLETED", total_inventory_cost=None),
    ]
    rows = [
        SimpleNamespace(scenario="proposed", shortage_qty=5.0),
        SimpleNamespace(scenario="proposed", shortage_qty=0.0),
        SimpleNamespace(scenario="baseline", shortage_qty=9.0),  # baseline tidak dihitung
    ]
    svc = DashboardService(
        FakeMaterials(1),
        FakeForecast(run, [_result(), _result(status="INSUFFICIENT_DATA")]),
        FakeReorder(recs),
        FakeOverride([]),
        projections=FakeProjections(rows),
    )

    s = await svc.summary(USER)

    assert s["attention"] == {"n_failed_products": 1, "n_missing_cost_data": 2, "n_shortage_periods": 1}


@pytest.mark.asyncio
async def test_attention_tanpa_run_none():
    svc = DashboardService(FakeMaterials(0), FakeForecast(None, []), FakeReorder([]), FakeOverride([]))
    assert (await svc.summary(USER))["attention"] is None



@pytest.mark.asyncio
async def test_latest_run_avg_mad_dan_mfe():
    # 21 Nov 2026 — tile akurasi memakai metrik MAD/MFE/MAPE (pengujian peramalan)
    run = SimpleNamespace(id="r1", status="COMPLETED")
    results = [_result(mad=4, mfe=-2, mape=10), _result(mad=6, mfe=1, mape=20), _result(status="INSUFFICIENT_DATA")]
    svc = DashboardService(FakeMaterials(1), FakeForecast(run, results), FakeReorder([]), FakeOverride([]))

    s = await svc.summary(USER)

    assert s["latest_run"]["avg_mad"] == pytest.approx(5.0)
    assert s["latest_run"]["avg_mfe"] == pytest.approx(-0.5)  # bertanda (arah bias)
    assert s["latest_run"]["avg_mape"] == pytest.approx(15.0)
