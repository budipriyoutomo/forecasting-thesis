"""Fase 11.6 — orkestrasi proyeksi stok per run (skenario usulan & baseline)."""
from datetime import date
from types import SimpleNamespace

import pytest

from app.services.stock_projection_service import StockProjectionService
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError

USER = "u1"


class Repo:
    def __init__(self):
        self.by_run = {}

    async def replace_for_run(self, run_id, rows):
        self.by_run[run_id] = rows
        return len(rows)

    async def list_by_run(self, run_id):
        return self.by_run.get(str(run_id), [])


class Forecast:
    def __init__(self, run, results):
        self._run, self._results = run, results

    async def get_run(self, run_id):
        return self._run if self._run and str(self._run.id) == str(run_id) else None

    async def list_results(self, run_id):
        return self._results


class Reorder:
    def __init__(self, recs):
        self._recs = recs

    async def list_by_run(self, run_id):
        return self._recs


class Boms:
    async def list(self, product_id=None):
        return [SimpleNamespace(product_id="p1", material_id="m1", qty_per_unit=1)]


class Demand:
    def __init__(self, rows):
        self._rows = rows

    async def list_for_product(self, pid, code):
        return self._rows


class Products:
    async def get_by_id(self, pid):
        return SimpleNamespace(id=pid, code="KBYPL 200")


class Configs:
    async def list(self):
        return [SimpleNamespace(item_type="material", material_id="m1", capacity_qty=2000),
                SimpleNamespace(item_type="product", product_id="p1", capacity_qty=1)]


class Stock:
    async def latest_stock(self, as_of=None):
        return {"m1": (date(2026, 10, 1), 1000.0)}


class Receipts:
    async def list(self, material_id=None, date_from=None, date_to=None):
        return [SimpleNamespace(material_id="m1", expected_date=date(2026, 11, 10), qty=200)]


def _svc(run=None, planning=None, recs=None, reorder_service=None):
    run = run or SimpleNamespace(id="r1", user_id=USER)
    fdata = [{"date": "2026-11-01", "value": 500}, {"date": "2026-12-01", "value": 400}]
    result = SimpleNamespace(product_id="p1", status="COMPLETED", forecast_data=fdata)
    repo = Repo()
    svc = StockProjectionService(
        repo, Forecast(run, [result]), Reorder(recs or []), Boms(), Demand(planning or []), Products(), Configs(),
        Stock(), Receipts(), reorder_service=reorder_service, factory=lambda **kw: SimpleNamespace(**kw),
    )
    return svc, repo


@pytest.mark.asyncio
async def test_proyeksi_usulan_dengan_stok_awal_kedatangan_kapasitas():
    rec = SimpleNamespace(material_id="m1", safety_stock=0, buffer_stock=0, eoq_qty=0)
    svc, repo = _svc(recs=[rec])
    rows = await svc.generate_for_run(USER, "r1")

    proposed = [r for r in rows if r.scenario == "proposed"]
    assert [(r.opening_qty, r.receipt_qty, r.usage_qty, r.ending_qty) for r in proposed] == [
        (1000, 200, 500, 700), (700, 0, 400, 300),
    ]
    assert proposed[0].capacity_qty == 2000 and proposed[0].utilization_ending_pct == pytest.approx(35)
    assert not [r for r in rows if r.scenario == "baseline"]  # planning horizon tidak tersedia
    assert repo.by_run["r1"] == rows


@pytest.mark.asyncio
async def test_skenario_baseline_bila_planning_horizon_ada():
    planning = [SimpleNamespace(period="2026-11-01", planning=600), SimpleNamespace(period="2026-12-01", planning=600)]
    rec = SimpleNamespace(material_id="m1", safety_stock=0, buffer_stock=0, eoq_qty=0)
    svc, _ = _svc(planning=planning, recs=[rec])
    rows = await svc.generate_for_run(USER, "r1")

    baseline = [r for r in rows if r.scenario == "baseline"]
    assert [r.usage_qty for r in baseline] == [600, 600]
    assert baseline[1].ending_qty == 0 and baseline[1].shortage_qty == 0  # 1000+200−600=600 → 600−600=0


@pytest.mark.asyncio
async def test_tanpa_reorder_tersimpan_dibuatkan_dulu():
    class ReorderSvc:
        called = False

        async def generate_for_run(self, user_id, run_id):
            ReorderSvc.called = True
            return [SimpleNamespace(material_id="m1", safety_stock=900, buffer_stock=0, eoq_qty=300)]

    svc, _ = _svc(reorder_service=ReorderSvc())
    rows = await svc.generate_for_run(USER, "r1")
    assert ReorderSvc.called
    assert rows[0].order_qty == 300  # pre 700 < level 900 → 1 × EOQ 300


@pytest.mark.asyncio
async def test_list_filter_dan_akses():
    svc, _ = _svc(recs=[SimpleNamespace(material_id="m1", safety_stock=0, buffer_stock=0, eoq_qty=0)])
    await svc.generate_for_run(USER, "r1")
    assert {r.scenario for r in await svc.list_for_run(USER, "r1", "proposed")} == {"proposed"}

    with pytest.raises(ForecastRunNotFoundError):
        await svc.list_for_run(USER, "zz")
    other, _ = _svc(run=SimpleNamespace(id="r1", user_id="u2"))
    with pytest.raises(ForbiddenRoleError):
        await other.generate_for_run(USER, "r1")
