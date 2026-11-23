"""
23 Nov 2026 (keputusan user) — EOQ dihitung dari TOTAL KEBUTUHAN material = MRP + SS + buffer
(bukan MRP saja), dan kebijakan qty pesan default = kelipatan EOQ. SS + B dibagi rata ke tiap
periode horizon supaya Σ deret EOQ = total kebutuhan (tab "3. Total kebutuhan").
"""
import math
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.cost_service import CostService
from app.services.reorder_service import (
    DEFAULT_ORDER_QTY_POLICY,
    ReorderService,
    compute_eoq,
    eoq_requirement_series,
)
from tests.unit.test_cost_service import (
    FakeBomRepo as CostBomRepo,
    FakeCostTemplateRepo as CostTemplateRepo,
    FakeDemandRepo,
    FakeForecastRepo as CostForecastRepo,
    FakeMaterialRepo as CostMaterialRepo,
    FakePlanningSettings as CostSettings,
    FakeProductRepo,
    FakeReorderRepo as CostReorderRepo,
    _demand_row,
)
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
    _priced,
    _run,
    _template,
    _tpl_rate,
)


def test_deret_eoq_mrp_plus_ss_dan_buffer_dibagi_rata():
    out = eoq_requirement_series([900, 1000, 1100], safety_stock=300, buffer=60)
    assert out == pytest.approx([1020, 1120, 1220])
    assert sum(out) == pytest.approx(3000 + 300 + 60)  # = total kebutuhan
    assert eoq_requirement_series([], 10, 5) == []


def test_default_kebijakan_qty_pesan_eoq():
    assert DEFAULT_ORDER_QTY_POLICY == "eoq"


@pytest.mark.asyncio
async def test_tanpa_settings_kebijakan_eoq():
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", [900, 1000, 1100])]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([_material("M1", "CAP", lead=7)]),
        cost_templates=FakeCostTemplateRepo(_template(Decimal("250000"), Decimal("10"))),
    )
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    assert r.order_qty_policy_used == "eoq"


@pytest.mark.asyncio
async def test_eoq_klasik_dari_total_kebutuhan():
    m1 = _priced("M1", "CAP", Decimal("1500"))
    m1.manual_safety_stock = Decimal("300")
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", [900, 1000, 1100])]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([m1]),
        cost_templates=FakeCostTemplateRepo(_tpl_rate(Decimal("250000"), Decimal("10"), Decimal("20"))),
        usage=FakeUsage({"M1": 1.05}),  # B = 0,05 × 1000 = 50
        settings=FakePlanningSettings("classic"),
    )
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]

    a = (3000 + 300 + 50) / 3 * 12  # total kebutuhan rata-rata per bulan × 12 = 13.400
    q = math.sqrt(2 * a * 250_000 / (0.20 * 1_500))
    assert float(r.annual_demand) == pytest.approx(a)
    assert float(r.eoq_raw_qty) == pytest.approx(q, abs=1e-3)
    assert float(r.mu_period) == pytest.approx(1000)  # SS/ROP tetap dari MRP


@pytest.mark.asyncio
async def test_eoq_dinamis_dari_total_kebutuhan():
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", [900, 1000, 1100])]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([_material("M1", "CAP", lead=7, manual_ss=Decimal("300"))]),
        cost_templates=FakeCostTemplateRepo(_template(Decimal("250000"), Decimal("10"))),
        settings=FakePlanningSettings("dynamic"),
    )
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    expected = compute_eoq(eoq_requirement_series([900, 1000, 1100], 300, 0), 250_000, 10)
    assert float(r.eoq_raw_qty) == pytest.approx(float(expected.eoq_qty), abs=1e-3)
    assert float(r.total_inventory_cost) == pytest.approx(float(expected.total_cost), abs=1e-2)


@pytest.mark.asyncio
async def test_baseline_tic_ikut_ss_dan_buffer_sistem():
    tpl = SimpleNamespace(name="T", ordering_cost=Decimal("250000"), holding_cost=Decimal("0"),
                          holding_cost_rate_pct=Decimal("20"))
    # SS di-adjust kapasitas jadi 100 → baseline memakai nilai SISTEM (300) + B 60
    rec = SimpleNamespace(material_id="M1", ordering_cost=Decimal("0"), holding_cost=Decimal("0"),
                          total_inventory_cost=Decimal("0"), safety_stock=Decimal("100"),
                          safety_stock_system=Decimal("300"), buffer_stock=Decimal("60"), buffer_stock_system=None)
    svc = CostService(
        forecast_repo=CostForecastRepo(SimpleNamespace(id="r1", user_id=USER),
                                       [SimpleNamespace(product_id="P1", status="COMPLETED", forecast_data=[])]),
        reorder_repo=CostReorderRepo([rec]),
        demand_repo=FakeDemandRepo({"P1": [_demand_row("SKU1", f"2026-0{i}-01", v) for i, v in ((1, 900), (2, 1000), (3, 1100))]}),
        boms=CostBomRepo({"P1": [SimpleNamespace(product_id="P1", material_id="M1", qty_per_unit=1)]}),
        products=FakeProductRepo([SimpleNamespace(id="P1", code="SKU1")]),
        cost_templates=CostTemplateRepo(tpl),
        materials=CostMaterialRepo([SimpleNamespace(id="M1", unit_price=Decimal("1500"))]),
        settings=CostSettings("classic"),
    )
    summary = await svc.get_cost_summary(USER, "r1")
    a = (3000 + 300 + 60) / 3 * 12
    q = math.sqrt(2 * a * 250_000 / (0.2 * 1500))
    assert float(summary.baseline_inventory_cost) == pytest.approx(2 * a / q * 250_000, rel=1e-4)
