"""
Fase 7 v3.0 — evaluasi kinerja inventory. Rumus (RECONCILIATION §Fase 7):
  shortage_t     = max(0, demand_t − supply_t)
  fill_rate      = 1 − Σshortage / Σdemand
  stock_out_rate = #periode(shortage>0) / T
  service_level  = 1 − stock_out_rate
  turnover       = Σdemand / rata-rata(supply)
Semua angka di bawah diverifikasi manual (AGENTS.md §3).
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.inventory_metrics_service import (
    InventoryMetricsService,
    compute_metrics,
    fill_rate,
    inventory_turnover,
    service_level,
    stock_out_rate,
)
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError

USER = "u1"
OTHER = "u2"


# ── Fungsi murni ──


def test_fill_rate():
    # demand 40, kekurangan 2 → 1 − 2/40 = 0.95
    assert fill_rate([10, 10, 10, 10], [10, 8, 10, 12]) == Decimal("0.95")


def test_stock_out_rate():
    # 1 dari 4 periode kekurangan → 0.25
    assert stock_out_rate([10, 10, 10, 10], [10, 8, 10, 12]) == Decimal("0.25")


def test_service_level():
    assert service_level([10, 10, 10, 10], [10, 8, 10, 12]) == Decimal("0.75")


def test_inventory_turnover():
    # Σdemand 40 ÷ rata-rata supply 10 = 4
    assert inventory_turnover([10, 10, 10, 10], [10, 8, 10, 12]) == Decimal("4")


def test_compute_metrics_bundle():
    m = compute_metrics([10, 10, 10, 10], [10, 8, 10, 12])
    assert (m.fill_rate, m.stock_out_rate, m.service_level, m.inventory_turnover) == (
        Decimal("0.95"),
        Decimal("0.25"),
        Decimal("0.75"),
        Decimal("4"),
    )


def test_empty_series_aman():
    m = compute_metrics([], [])
    assert m.fill_rate == Decimal("1")
    assert m.service_level == Decimal("1")
    assert m.stock_out_rate == Decimal("0")
    assert m.inventory_turnover == Decimal("0")


def test_zero_demand_tidak_dianggap_stockout():
    m = compute_metrics([0, 0], [5, 5])
    assert m.fill_rate == Decimal("1")
    assert m.stock_out_rate == Decimal("0")
    assert m.inventory_turnover == Decimal("0")


def test_avg_supply_nol_turnover_nol():
    assert inventory_turnover([10, 10], [0, 0]) == Decimal("0")


# ── Orkestrasi ──


def _demand_row(code, period, actual, planning):
    return SimpleNamespace(
        product_code=code,
        period=date.fromisoformat(period),
        actual=Decimal(str(actual)),
        planning=None if planning is None else Decimal(str(planning)),
    )


def _result(product_id, forecast_data, status="COMPLETED"):
    return SimpleNamespace(product_id=product_id, status=status, forecast_data=forecast_data)


class FakeForecastRepo:
    def __init__(self, run, results):
        self._run = run
        self._results = results

    async def get_run(self, run_id):
        return self._run if self._run and str(self._run.id) == str(run_id) else None

    async def list_results(self, run_id):
        return self._results


class FakeDemandRepo:
    def __init__(self, rows_by_pid):
        self._rows = rows_by_pid

    async def list_for_product(self, product_id, product_code):
        return self._rows.get(str(product_id), [])


class FakeProductRepo:
    def __init__(self, products):
        self._by_id = {str(p.id): p for p in products}

    async def get_by_id(self, pid):
        return self._by_id.get(str(pid))


class FakeMetricsRepo:
    def __init__(self):
        self.saved = None

    async def replace_for_run(self, run_id, rows):
        self.saved = rows
        return rows

    async def list_by_run(self, run_id):
        return self.saved or []


def _service(run=None, results=None, demand=None, products=None, metrics_repo=None):
    return InventoryMetricsService(
        forecast_repo=FakeForecastRepo(run, results or []),
        demand_repo=FakeDemandRepo(demand or {}),
        products=FakeProductRepo(products or []),
        metrics_repo=metrics_repo or FakeMetricsRepo(),
    )


@pytest.mark.asyncio
async def test_compute_baseline_dan_forecastiq():
    run = SimpleNamespace(id="r1", user_id=USER)
    rows = [
        _demand_row("SKU1", "2026-01-01", 10, 10),
        _demand_row("SKU1", "2026-02-01", 10, 8),
        _demand_row("SKU1", "2026-03-01", 10, 10),
    ]
    forecast_data = [
        {"date": "2026-01-01", "value": 9, "lower": 0, "upper": 0},
        {"date": "2026-02-01", "value": 11, "lower": 0, "upper": 0},
        {"date": "2026-03-01", "value": 10, "lower": 0, "upper": 0},
    ]
    repo = FakeMetricsRepo()
    svc = _service(
        run=run,
        results=[_result("P1", forecast_data)],
        demand={"P1": rows},
        products=[SimpleNamespace(id="P1", code="SKU1")],
        metrics_repo=repo,
    )
    out = await svc.compute_for_run(USER, "r1")

    baseline = next(m for m in out if m.scope == "baseline")
    forecastiq = next(m for m in out if m.scope == "forecastiq")

    # baseline: demand[10,10,10] supply[10,8,10] → shortage 2, fill 1−2/30
    assert baseline.target_type == "product"
    assert baseline.fill_rate == Decimal("0.9333")
    assert baseline.stock_out_rate == Decimal("0.3333")
    # forecastiq: supply[9,11,10] → shortage 1 → fill 1−1/30
    assert forecastiq.fill_rate == Decimal("0.9667")
    assert repo.saved is out  # dipersist


@pytest.mark.asyncio
async def test_forecastiq_skip_bila_tak_ada_irisan_periode():
    run = SimpleNamespace(id="r1", user_id=USER)
    rows = [_demand_row("SKU1", "2026-01-01", 10, 10)]
    forecast_data = [{"date": "2026-09-01", "value": 9, "lower": 0, "upper": 0}]
    svc = _service(
        run=run,
        results=[_result("P1", forecast_data)],
        demand={"P1": rows},
        products=[SimpleNamespace(id="P1", code="SKU1")],
    )
    out = await svc.compute_for_run(USER, "r1")
    assert [m.scope for m in out] == ["baseline"]


@pytest.mark.asyncio
async def test_result_gagal_dilewati():
    run = SimpleNamespace(id="r1", user_id=USER)
    svc = _service(
        run=run,
        results=[_result("P1", None, status="MODEL_SELECTION_FAILED")],
        demand={"P1": [_demand_row("SKU1", "2026-01-01", 10, 10)]},
        products=[SimpleNamespace(id="P1", code="SKU1")],
    )
    out = await svc.compute_for_run(USER, "r1")
    assert out == []


@pytest.mark.asyncio
async def test_run_tidak_ada_404():
    svc = _service(run=None)
    with pytest.raises(ForecastRunNotFoundError):
        await svc.compute_for_run(USER, "ghost")


@pytest.mark.asyncio
async def test_run_milik_user_lain_403():
    run = SimpleNamespace(id="r1", user_id=OTHER)
    svc = _service(run=run)
    with pytest.raises(ForbiddenRoleError):
        await svc.compute_for_run(USER, "r1")
