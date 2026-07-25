"""
Swap v3.0 — ReorderService per MATERIAL dari breakdown BOM atas forecast produk.
Repo/forecast/BOM/material di-mock.
"""
from types import SimpleNamespace

import pytest

from app.services.reorder_service import ReorderService
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError

USER = "u1"
OTHER = "u2"


class FakeForecastRepo:
    def __init__(self, run, results):
        self._run = run
        self._results = results

    async def get_run(self, run_id):
        return self._run if self._run and str(self._run.id) == str(run_id) else None

    async def list_results(self, run_id):
        return self._results


class FakeBomRepo:
    def __init__(self, boms_by_product):
        self._by_product = boms_by_product

    async def list(self, product_id=None):
        return self._by_product.get(product_id, [])


class FakeMaterialRepo:
    def __init__(self, materials):
        self._by_id = {str(m.id): m for m in materials}

    async def get_by_id(self, mid):
        return self._by_id.get(str(mid))


class FakeReorderRepo:
    def __init__(self):
        self.by_run = {}

    async def replace_for_run(self, run_id, recs):
        self.by_run[str(run_id)] = list(recs)
        return len(recs)

    async def list_by_run(self, run_id):
        return self.by_run.get(str(run_id), [])


def _run(rid="r1", user=USER):
    return SimpleNamespace(id=rid, user_id=user)


def _result(pid, values, status="COMPLETED"):
    fdata = [{"value": v} for v in values]
    return SimpleNamespace(product_id=pid, status=status, forecast_data=fdata)


def _material(mid, code, lead=4, moq=0, manual_ss=None):
    return SimpleNamespace(id=mid, code=code, lead_time_days=lead, moq=moq, manual_safety_stock=manual_ss)


def _bom(pid, mid, qty):
    return SimpleNamespace(product_id=pid, material_id=mid, qty_per_unit=qty)


def _service(run, results, boms_by_product, materials):
    return ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(run, results),
        boms=FakeBomRepo(boms_by_product),
        materials=FakeMaterialRepo(materials),
    )


@pytest.mark.asyncio
async def test_generate_rekomendasi_per_material_dari_breakdown():
    svc = _service(
        _run(),
        [_result("p1", [10, 12, 11, 9, 10, 11])],
        {"p1": [_bom("p1", "M1", 2), _bom("p1", "M2", 1)]},
        [_material("M1", "RM-001"), _material("M2", "RM-002")],
    )

    recs = await svc.generate_for_run(USER, "r1", current_stock={"M1": 0, "M2": 0})

    by_material = {str(r.material_id): r for r in recs}
    assert set(by_material) == {"M1", "M2"}
    # M1 (qty 2) demand 2× lebih besar → reorder point lebih besar dari M2 (qty 1)
    assert float(by_material["M1"].reorder_point) > float(by_material["M2"].reorder_point)
    assert all(r.status in ("urgent", "safe", "overstock") for r in recs)


@pytest.mark.asyncio
async def test_generate_menyertakan_eoq_dan_biaya():
    svc = _service(
        _run(),
        [_result("p1", [10, 12, 11, 9])],
        {"p1": [_bom("p1", "M1", 1)]},
        [_material("M1", "RM-001", moq=500)],
    )

    recs = await svc.generate_for_run(USER, "r1", current_stock={"M1": 0})

    r = recs[0]
    assert r.eoq_qty is not None and float(r.eoq_qty) >= 500  # dibulatkan ke MOQ
    assert r.total_inventory_cost is not None


@pytest.mark.asyncio
async def test_generate_lewati_produk_forecast_gagal():
    svc = _service(
        _run(),
        [_result("p1", [], status="INSUFFICIENT_DATA")],
        {"p1": [_bom("p1", "M1", 2)]},
        [_material("M1", "RM-001")],
    )

    recs = await svc.generate_for_run(USER, "r1")

    assert recs == []  # produk gagal → tak ada deret → tak ada material


@pytest.mark.asyncio
async def test_generate_run_tidak_ada_404():
    svc = _service(None, [], {}, [])
    with pytest.raises(ForecastRunNotFoundError):
        await svc.generate_for_run(USER, "r1")


@pytest.mark.asyncio
async def test_generate_run_milik_user_lain_403():
    svc = _service(_run(user=OTHER), [], {}, [])
    with pytest.raises(ForbiddenRoleError):
        await svc.generate_for_run(USER, "r1")


@pytest.mark.asyncio
async def test_list_filter_status():
    svc = _service(
        _run(),
        [_result("p1", [10, 12, 11, 9, 10, 11])],
        {"p1": [_bom("p1", "M1", 1), _bom("p1", "M2", 1)]},
        [_material("M1", "RM-001"), _material("M2", "RM-002")],
    )
    # M1 stok 0 → urgent ; M2 stok sangat besar → overstock
    await svc.generate_for_run(USER, "r1", current_stock={"M1": 0, "M2": 100000})

    urgent = await svc.list_for_run(USER, "r1", status="urgent")
    overstock = await svc.list_for_run(USER, "r1", status="overstock")

    assert all(r.status == "urgent" for r in urgent)
    assert all(r.status == "overstock" for r in overstock)
    assert len(urgent) >= 1 and len(overstock) >= 1
