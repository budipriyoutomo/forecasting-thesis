"""
Fase 5 — ReorderService orkestrasi (generate + list), repo/forecast/material di-mock.
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


class FakeMaterialRepo:
    def __init__(self, materials):
        self._by_id = {str(m.id): m for m in materials}

    async def get_by_id(self, mid):
        return self._by_id.get(str(mid))


class FakeConsumptionRepo:
    def __init__(self, rows_by_material):
        self._rows = rows_by_material

    async def list_for_material(self, material_id, material_code):
        return self._rows.get(str(material_id), [])


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


def _result(mid, status="COMPLETED"):
    return SimpleNamespace(material_id=mid, status=status)


def _material(mid, code, lead=4, moq=0, manual_ss=None):
    return SimpleNamespace(id=mid, code=code, lead_time_days=lead, moq=moq, manual_safety_stock=manual_ss)


def _rows(quantities, start="2026-01-01"):
    import pandas as pd

    dates = pd.date_range(start, periods=len(quantities), freq="D")
    return [SimpleNamespace(date=str(d.date()), quantity=q) for d, q in zip(dates, quantities)]


def _service(run, results, materials, rows_by_material):
    return ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(run, results),
        materials=FakeMaterialRepo(materials),
        consumptions=FakeConsumptionRepo(rows_by_material),
    )


@pytest.mark.asyncio
async def test_generate_membuat_rekomendasi_per_material_completed():
    svc = _service(
        _run(),
        [_result("m1"), _result("m2")],
        [_material("m1", "RM-001", lead=4), _material("m2", "RM-002", lead=7)],
        {"m1": _rows([10, 12, 11, 9, 10, 11, 10, 12]), "m2": _rows([5, 6, 5, 4, 5, 6, 5])},
    )

    recs = await svc.generate_for_run(USER, "r1", current_stock={"m1": 0, "m2": 0})

    assert len(recs) == 2
    assert all(r.status in ("urgent", "safe", "overstock") for r in recs)
    assert all(float(r.reorder_point) > 0 for r in recs)


@pytest.mark.asyncio
async def test_generate_lewati_material_forecast_gagal():
    svc = _service(
        _run(),
        [_result("m1", status="INSUFFICIENT_DATA")],
        [_material("m1", "RM-001")],
        {"m1": _rows([10, 12, 11])},
    )

    recs = await svc.generate_for_run(USER, "r1")

    assert recs == []


@pytest.mark.asyncio
async def test_generate_run_tidak_ada_404():
    svc = _service(None, [], [], {})
    with pytest.raises(ForecastRunNotFoundError):
        await svc.generate_for_run(USER, "r1")


@pytest.mark.asyncio
async def test_generate_run_milik_user_lain_403():
    svc = _service(_run(user=OTHER), [], [], {})
    with pytest.raises(ForbiddenRoleError):
        await svc.generate_for_run(USER, "r1")


@pytest.mark.asyncio
async def test_list_filter_status():
    svc = _service(
        _run(),
        [_result("m1"), _result("m2")],
        # m1 stok 0 → urgent ; m2 stok sangat besar → overstock
        [_material("m1", "RM-001"), _material("m2", "RM-002")],
        {"m1": _rows([10, 12, 11, 9, 10, 11]), "m2": _rows([10, 12, 11, 9, 10, 11])},
    )
    await svc.generate_for_run(USER, "r1", current_stock={"m1": 0, "m2": 100000})

    urgent = await svc.list_for_run(USER, "r1", status="urgent")
    overstock = await svc.list_for_run(USER, "r1", status="overstock")

    assert all(r.status == "urgent" for r in urgent)
    assert all(r.status == "overstock" for r in overstock)
    assert len(urgent) >= 1 and len(overstock) >= 1
