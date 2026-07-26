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

    async def get_latest_run_for_user(self, user_id):
        return self._run

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


def _result(status="COMPLETED", mase=None, mape=None):
    return SimpleNamespace(
        status=status,
        mase=Decimal(str(mase)) if mase is not None else None,
        mape=Decimal(str(mape)) if mape is not None else None,
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
        is_within_capacity=True, total_pallet_required=Decimal("3"), total_pallet_capacity=Decimal("100")
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
    assert s["warehouse"]["total_pallet_required"] == pytest.approx(3)
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
