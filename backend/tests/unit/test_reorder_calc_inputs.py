"""
23 Nov 2026 — input perhitungan SS/ROP/EOQ ikut disimpan per rekomendasi supaya UI
"Perencanaan persediaan" bisa MENAMPILKAN perhitungannya (μ, σ, Z, L, EOQ sebelum MOQ,
S & H) tanpa merumuskan ulang di frontend (AGENTS.md §11: rumus hanya di reorder_service).
"""
import math
from decimal import Decimal

import numpy as np
import pytest

from app.api.v1.reorder import _out
from app.services.reorder_service import ReorderService, z_from_service_level
from tests.unit.test_reorder_service import (
    USER,
    FakeBomRepo,
    FakeCostTemplateRepo,
    FakeForecastRepo,
    FakeMaterialRepo,
    FakePlanningSettings,
    FakeReorderRepo,
    _bom,
    _dated_result,
    _material,
    _priced,
    _run,
    _tpl_rate,
)


@pytest.mark.asyncio
async def test_input_ss_dan_rop_disimpan():
    values = [300, 360, 240, 300]  # bulanan → 31 hari per periode
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", values)]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 2)]}),
        materials=FakeMaterialRepo([_material("M1", "RM-001", lead=7)]),
        settings=FakePlanningSettings("dynamic", service_level_pct=99.0),
    )
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]

    series = [v * 2 for v in values]
    assert float(r.mu_period) == pytest.approx(np.mean(series), abs=1e-3)
    assert float(r.sigma_period) == pytest.approx(np.std(series, ddof=1), abs=1e-3)
    assert float(r.period_days) == 31
    assert float(r.lead_time_days_used) == 7
    assert float(r.service_level_pct_used) == 99
    assert float(r.z_value) == pytest.approx(z_from_service_level(99), abs=1e-4)
    # input yang disimpan cukup untuk merekonstruksi SS & ROP tersimpan (verifikasi manual)
    sigma_d = float(r.sigma_period) / math.sqrt(31)
    assert float(r.safety_stock) == pytest.approx(float(r.z_value) * sigma_d * math.sqrt(7), rel=1e-4)
    mu_d = float(r.mu_period) / 31
    assert float(r.reorder_point) == pytest.approx(mu_d * 7 + float(r.safety_stock) + float(r.buffer_stock), rel=1e-4)


@pytest.mark.asyncio
async def test_input_eoq_klasik_disimpan_sebelum_pembulatan_moq():
    values = [900, 1000, 1100]  # A = 12.000
    m1 = _priced("M1", "CAP", Decimal("1500"))
    m1.moq = 5000
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", values)]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([m1]),
        cost_templates=FakeCostTemplateRepo(_tpl_rate(Decimal("250000"), Decimal("10"), Decimal("20"))),
        settings=FakePlanningSettings("classic"),
    )
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]

    a = (3000 + float(r.safety_stock) + float(r.buffer_stock)) / 3 * 12  # total kebutuhan (23 Nov 2026)
    q = math.sqrt(2 * a * 250_000 / (0.20 * 1_500))
    assert float(r.eoq_raw_qty) == pytest.approx(q, abs=1e-3)
    assert float(r.eoq_qty) == 5000  # dibulatkan ke kelipatan MOQ
    assert float(r.ordering_cost_per_order) == 250_000
    assert float(r.holding_cost_per_unit) == 10


def test_out_menyertakan_input_perhitungan():
    from types import SimpleNamespace

    rec = SimpleNamespace(
        id="x", material_id="M1", safety_stock=Decimal("1"), reorder_point=Decimal("2"),
        recommended_order_qty=Decimal("0"), status="safe", mu_period=Decimal("10"),
        sigma_period=Decimal("2"), period_days=Decimal("31"), lead_time_days_used=Decimal("7"),
        z_value=Decimal("1.6449"), service_level_pct_used=Decimal("95"), eoq_raw_qty=Decimal("12.5"),
        ordering_cost_per_order=Decimal("100"), holding_cost_per_unit=Decimal("5"),
    )
    out = _out(rec)
    assert out["mu_period"] == "10" and out["z_value"] == "1.6449"
    assert out["eoq_raw_qty"] == "12.5" and out["holding_cost_per_unit"] == "5"
