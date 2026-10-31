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


# ── Fase 11.7: evaluasi level MATERIAL + inventory days + shortage cost ──

from app.services.inventory_metrics_service import (  # noqa: E402
    allocate_shortage,
    inventory_days,
    material_metrics,
    shortage_cost,
)


def test_inventory_days_thesis():
    # rata-rata persediaan 3.000 ÷ rata-rata pemakaian per hari (3.100 / 31 = 100) = 30 hari
    assert inventory_days(avg_inventory=3000, avg_daily_usage=100) == pytest.approx(30)
    assert inventory_days(avg_inventory=3000, avg_daily_usage=0) is None


def test_shortage_cost_produk():
    assert shortage_cost({"p1": 10, "p2": 5}, {"p1": Decimal("7000"), "p2": None}) == pytest.approx(70_000)


def test_alokasi_shortage_material_bersama():
    # Bottle dipakai p1 (600) & p2 (400), qty BOM 1 → shortage 100 dibagi 60:40
    units = allocate_shortage(100, {"p1": 600, "p2": 400}, {"p1": 1, "p2": 1})
    assert units == pytest.approx({"p1": 60, "p2": 40})
    assert allocate_shortage(100, {}, {}) == {}


def _proj(opening, usage, ending, shortage):
    return SimpleNamespace(opening_qty=opening, usage_qty=usage, ending_qty=ending, shortage_qty=shortage)


def test_material_metrics_dari_proyeksi():
    rows = [_proj(1000, 600, 400, 0), _proj(400, 500, 0, 100)]
    m = material_metrics(rows, days_per_period=30)

    assert float(m.fill_rate) == pytest.approx(1 - 100 / 1100, abs=1e-4)
    assert float(m.stock_out_rate) == pytest.approx(0.5)
    assert float(m.service_level) == pytest.approx(0.5)
    avg_stock = ((1000 + 400) / 2 + (400 + 0) / 2) / 2  # 450
    assert float(m.inventory_days) == pytest.approx(avg_stock / (1100 / 60), abs=1e-4)
    assert float(m.inventory_turnover) == pytest.approx(1100 / avg_stock, abs=1e-4)


class FakeProjections:
    def __init__(self, rows):
        self._rows = rows

    async def list_by_run(self, run_id):
        return self._rows


class FakeBoms:
    async def list(self, product_id=None):
        return [SimpleNamespace(product_id="P1", material_id="M1", qty_per_unit=1)]


@pytest.mark.asyncio
async def test_compute_menambah_scope_material_dan_shortage_cost():
    from datetime import date

    run = SimpleNamespace(id="r1", user_id=USER)
    fdata = [{"date": "2026-11-01", "value": 600}, {"date": "2026-12-01", "value": 500}]
    proj = [
        SimpleNamespace(material_id="M1", scenario="proposed", period=date(2026, 11, 1), opening_qty=1000,
                        usage_qty=600, ending_qty=400, shortage_qty=0),
        SimpleNamespace(material_id="M1", scenario="proposed", period=date(2026, 12, 1), opening_qty=400,
                        usage_qty=500, ending_qty=0, shortage_qty=100),
    ]
    svc = InventoryMetricsService(
        forecast_repo=FakeForecastRepo(run, [SimpleNamespace(product_id="P1", status="COMPLETED", forecast_data=fdata)]),
        demand_repo=FakeDemandRepo({}),
        products=FakeProductRepo([SimpleNamespace(id="P1", code="SKU1", selling_price=Decimal("7000"))]),
        metrics_repo=FakeMetricsRepo(),
        projections=FakeProjections(proj),
        boms=FakeBoms(),
    )
    rows = await svc.compute_for_run(USER, "r1")

    mat = [r for r in rows if r.target_type == "material"]
    assert len(mat) == 1 and mat[0].scope == "forecastiq" and str(mat[0].target_id) == "M1"
    assert float(mat[0].shortage_cost) == pytest.approx(100 * 7000)
    assert mat[0].inventory_days is not None


@pytest.mark.asyncio
async def test_baris_produk_punya_shortage_cost():
    run = SimpleNamespace(id="r1", user_id=USER)
    drows = [SimpleNamespace(period="2026-01-01", actual=100, planning=90),
             SimpleNamespace(period="2026-02-01", actual=100, planning=100)]
    svc = InventoryMetricsService(
        forecast_repo=FakeForecastRepo(run, [SimpleNamespace(product_id="P1", status="COMPLETED", forecast_data=[])]),
        demand_repo=FakeDemandRepo({"P1": drows}),
        products=FakeProductRepo([SimpleNamespace(id="P1", code="SKU1", selling_price=Decimal("7000"))]),
        metrics_repo=FakeMetricsRepo(),
    )
    rows = await svc.compute_for_run(USER, "r1")
    assert float(rows[0].shortage_cost) == pytest.approx(10 * 7000)
