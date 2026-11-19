"""
Fase 11.17 — ReorderService memakai adjust kapasitas (SS & Buffer) per run.

Data: kebutuhan bulanan [800, 1200, 1000] (Jan–Mar 2026 → 29,5 hari/periode), lead time
29,5 hari → μ·L = 1000, σ_d·√L = 200. Faktor waste 1,05 → Buffer = 0,05 × 1000 = 50.
Target service level 99% → SS = 2,3263 × 200 = 465,27.
"""
from decimal import Decimal
from statistics import NormalDist
from types import SimpleNamespace

import pytest

from app.services.capacity_adjustment_service import as_adjustment
from app.services.reorder_service import ReorderService, system_policy_from_rec
from tests.unit.test_reorder_service import (
    USER,
    FakeBomRepo,
    FakeCostTemplateRepo,
    FakeForecastRepo,
    FakeMaterialRepo,
    FakePlanningSettings,
    FakeReorderRepo,
    FakeUsage,
    _bom,
    _dated_result,
    _material,
    _run,
    _template,
)

LEAD = 29.5
SIGMA_LT = 200.0


def _z(pct):
    return NormalDist().inv_cdf(pct / 100)


class Adjustments:
    def __init__(self, mapping):
        self._m = mapping

    async def adjustments_by_material(self, run_id):
        return self._m


def _svc(manual_ss=None, adjustments=None):
    repo = FakeReorderRepo()
    svc = ReorderService(
        reorder_repo=repo,
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", [800, 1200, 1000])]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([_material("M1", "CAP", lead=LEAD, manual_ss=manual_ss)]),
        cost_templates=FakeCostTemplateRepo(_template(Decimal("100"), Decimal("1"))),
        usage=FakeUsage({"M1": 1.05}),
        settings=FakePlanningSettings("dynamic", service_level_pct=99.0),
        adjustments=adjustments,
    )
    return svc, repo


@pytest.mark.asyncio
async def test_tanpa_adjust_nilai_sistem_dan_service_level_efektif():
    svc, _ = _svc()
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    assert float(r.safety_stock) == pytest.approx(_z(99) * SIGMA_LT, abs=1e-3)
    assert float(r.buffer_stock) == pytest.approx(50)
    assert float(r.service_level_effective) == pytest.approx(99, abs=1e-3)
    assert r.safety_stock_system is None and r.buffer_stock_system is None
    assert r.adjustment_source is None


@pytest.mark.asyncio
async def test_adjust_service_level_menurunkan_ss_rop_dan_s():
    svc, _ = _svc(adjustments=Adjustments({"M1": as_adjustment(service_level_pct=97)}))
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    ss = _z(97) * SIGMA_LT
    assert float(r.safety_stock) == pytest.approx(ss, abs=1e-3)
    assert float(r.reorder_point) == pytest.approx(1000 + ss + 50, abs=1e-3)
    assert float(r.order_up_to_level) == pytest.approx(2000 + ss + 50, abs=1e-3)
    assert float(r.service_level_effective) == pytest.approx(97, abs=1e-3)
    # Nilai sistem disimpan untuk audit & skenario baseline
    assert float(r.safety_stock_system) == pytest.approx(_z(99) * SIGMA_LT, abs=1e-3)
    assert float(r.buffer_stock_system) == pytest.approx(50)
    assert r.adjustment_source == "suggested"


@pytest.mark.asyncio
async def test_adjust_custom_qty_ss_dan_buffer():
    adj = as_adjustment(safety_stock=300, buffer_stock=20, source="custom")
    svc, _ = _svc(adjustments=Adjustments({"M1": adj}))
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    assert float(r.safety_stock) == pytest.approx(300)
    assert float(r.buffer_stock) == pytest.approx(20)
    assert float(r.reorder_point) == pytest.approx(1320)
    assert float(r.order_up_to_level) == pytest.approx(2320)
    assert float(r.service_level_effective) == pytest.approx(NormalDist().cdf(1.5) * 100, abs=1e-3)
    assert r.adjustment_source == "custom"


@pytest.mark.asyncio
async def test_service_level_tidak_mengubah_ss_manual():
    svc, _ = _svc(manual_ss=400, adjustments=Adjustments({"M1": as_adjustment(service_level_pct=90)}))
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    assert float(r.safety_stock) == pytest.approx(400)


@pytest.mark.asyncio
async def test_compute_tidak_menyimpan_dan_adjust_eksplisit_mengabaikan_tersimpan():
    svc, repo = _svc(adjustments=Adjustments({"M1": as_adjustment(safety_stock=0, buffer_stock=0)}))
    recs = await svc.compute_for_run(USER, "r1", current_stock={"M1": 0}, adjustments={})
    assert repo.by_run == {}
    assert float(recs[0].safety_stock) == pytest.approx(_z(99) * SIGMA_LT, abs=1e-3)


@pytest.mark.asyncio
async def test_kebijakan_sistem_merekonstruksi_rop_sebelum_adjust():
    adj = as_adjustment(safety_stock=300, buffer_stock=20, source="custom")
    svc, _ = _svc(adjustments=Adjustments({"M1": adj}))
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    p = system_policy_from_rec(r)
    ss_sys = _z(99) * SIGMA_LT
    assert p.reorder_point == pytest.approx(1000 + ss_sys + 50, abs=1e-3)
    assert p.order_up_to == pytest.approx(2000 + ss_sys + 50, abs=1e-3)


def test_kebijakan_sistem_rumus_standard_buffer_tidak_menggeser_rop():
    rec = SimpleNamespace(
        reorder_point=1300, order_up_to_level=2300, safety_stock=300, buffer_stock=0,
        safety_stock_system=400, buffer_stock_system=50, rop_formula_used="standard",
        order_qty_policy_used="order_up_to", eoq_qty=0, moq_used=0,
    )
    p = system_policy_from_rec(rec)
    assert (p.reorder_point, p.order_up_to) == (1400, 2400)


def test_kebijakan_sistem_tanpa_adjust_sama_dengan_rekomendasi():
    rec = SimpleNamespace(
        reorder_point=1300, order_up_to_level=2300, safety_stock=300, buffer_stock=0,
        safety_stock_system=None, buffer_stock_system=None, order_qty_policy_used="eoq", eoq_qty=500, moq_used=0,
    )
    p = system_policy_from_rec(rec)
    assert (p.reorder_point, p.order_up_to, p.policy) == (1300, 2300, "eoq")
