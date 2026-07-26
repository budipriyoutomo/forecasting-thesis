"""
Fase 7 v3.0 — ringkasan total biaya persediaan (TIC) & % penghematan.
TIC & savings pakai rumus ARCHITECTURE §6.8 (fungsi murni di reorder_service,
di-reuse — RECONCILIATION §Fase 7). Angka diverifikasi manual (AGENTS.md §3).
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.cost_service import CostService, aggregate_proposed
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError

USER = "u1"
OTHER = "u2"


def _rec(mid, ordering, holding, tic):
    return SimpleNamespace(
        material_id=mid,
        ordering_cost=Decimal(str(ordering)),
        holding_cost=Decimal(str(holding)),
        total_inventory_cost=Decimal(str(tic)),
    )


def test_aggregate_proposed_menjumlahkan():
    ordering, holding, tic = aggregate_proposed([_rec("M1", 100, 20, 120), _rec("M2", 100, 0, 100)])
    assert (ordering, holding, tic) == (Decimal("200"), Decimal("20"), Decimal("220"))


# ── Orkestrasi ──


def _demand_row(code, period, planning):
    return SimpleNamespace(product_code=code, period=period, planning=Decimal(str(planning)), actual=Decimal("0"))


class FakeForecastRepo:
    def __init__(self, run, results):
        self._run = run
        self._results = results

    async def get_run(self, run_id):
        return self._run if self._run and str(self._run.id) == str(run_id) else None

    async def list_results(self, run_id):
        return self._results


class FakeReorderRepo:
    def __init__(self, recs):
        self._recs = recs

    async def list_by_run(self, run_id):
        return self._recs


class FakeDemandRepo:
    def __init__(self, rows_by_pid):
        self._rows = rows_by_pid

    async def list_for_product(self, product_id, product_code):
        return self._rows.get(str(product_id), [])


class FakeBomRepo:
    def __init__(self, lines_by_pid):
        self._by_pid = lines_by_pid

    async def list(self, product_id):
        return self._by_pid.get(str(product_id), [])


class FakeProductRepo:
    def __init__(self, products):
        self._by_id = {str(p.id): p for p in products}

    async def get_by_id(self, pid):
        return self._by_id.get(str(pid))


def _service(run=None, results=None, recs=None, demand=None, boms=None, products=None, S=100, H=0):
    return CostService(
        forecast_repo=FakeForecastRepo(run, results or []),
        reorder_repo=FakeReorderRepo(recs or []),
        demand_repo=FakeDemandRepo(demand or {}),
        boms=FakeBomRepo(boms or {}),
        products=FakeProductRepo(products or []),
        ordering_cost=S,
        holding_cost=H,
    )


@pytest.mark.asyncio
async def test_cost_summary_savings():
    run = SimpleNamespace(id="r1", user_id=USER)
    # baseline: planning [10,10,10] → material M1 (qty 1) → EOQ cost = 100 (S=100,H=0,n=1)
    # proposed: rec M1 tic 80 → savings (100−80)/100 = 20%
    svc = _service(
        run=run,
        results=[SimpleNamespace(product_id="P1", status="COMPLETED", forecast_data=[])],
        recs=[_rec("M1", 80, 0, 80)],
        demand={"P1": [_demand_row("SKU1", f"2026-0{i}-01", 10) for i in (1, 2, 3)]},
        boms={"P1": [SimpleNamespace(product_id="P1", material_id="M1", qty_per_unit=1)]},
        products=[SimpleNamespace(id="P1", code="SKU1")],
        S=100,
        H=0,
    )
    out = await svc.get_cost_summary(USER, "r1")
    assert out.total_inventory_cost == Decimal("80")
    assert out.baseline_inventory_cost == Decimal("100")
    assert out.savings_pct == Decimal("20")


@pytest.mark.asyncio
async def test_cost_summary_baseline_nol_savings_nol():
    run = SimpleNamespace(id="r1", user_id=USER)
    svc = _service(run=run, results=[], recs=[_rec("M1", 0, 0, 50)], demand={}, boms={}, products=[])
    out = await svc.get_cost_summary(USER, "r1")
    assert out.baseline_inventory_cost == Decimal("0")
    assert out.savings_pct == Decimal("0")


@pytest.mark.asyncio
async def test_run_tidak_ada_404():
    svc = _service(run=None)
    with pytest.raises(ForecastRunNotFoundError):
        await svc.get_cost_summary(USER, "ghost")


@pytest.mark.asyncio
async def test_run_milik_user_lain_403():
    run = SimpleNamespace(id="r1", user_id=OTHER)
    svc = _service(run=run)
    with pytest.raises(ForbiddenRoleError):
        await svc.get_cost_summary(USER, "r1")
