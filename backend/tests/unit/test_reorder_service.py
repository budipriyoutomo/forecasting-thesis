"""
Swap v3.0 — ReorderService per MATERIAL dari breakdown BOM atas forecast produk.
Repo/forecast/BOM/material di-mock.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.services.reorder_service import ReorderService, compute_eoq
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


# ── S & H dari template biaya aktif (Fase 10.6) ──


class FakeCostTemplateRepo:
    def __init__(self, active=None):
        self._active = active

    async def get_active(self):
        return self._active


def _template(S, H):
    return SimpleNamespace(name="Template 2026", ordering_cost=S, holding_cost=H, is_active=True)


@pytest.mark.asyncio
async def test_generate_pakai_s_dan_h_template_aktif():
    # H = 0 → EOQ memilih n = 1 pesanan; ordering = 1 × S template = 1.000.000
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_result("p1", [10, 12, 11, 9])]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([_material("M1", "RM-001")]),
        cost_templates=FakeCostTemplateRepo(_template(Decimal("1000000"), Decimal("0"))),
    )
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    assert float(r.ordering_cost) == 1_000_000
    assert float(r.holding_cost) == 0
    assert float(r.total_inventory_cost) == 1_000_000


@pytest.mark.asyncio
async def test_generate_tanpa_template_aktif_fallback_env():
    settings = get_settings()
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_result("p1", [10, 12, 11, 9])]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([_material("M1", "RM-001")]),
        cost_templates=FakeCostTemplateRepo(None),
    )
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    expected = compute_eoq([10, 12, 11, 9], settings.DEFAULT_ORDERING_COST, settings.DEFAULT_HOLDING_COST_RATE)
    assert float(r.total_inventory_cost) == pytest.approx(float(expected.total_cost))


# ── Satuan periode → harian untuk SS/ROP (Fase 11.0, REVISI_V2 §3.7) ──


def _dated_result(pid, values, start_month=1):
    fdata = [{"date": f"2026-{start_month + i:02d}-01", "value": v} for i, v in enumerate(values)]
    return SimpleNamespace(product_id=pid, status="COMPLETED", forecast_data=fdata)


@pytest.mark.asyncio
async def test_generate_forecast_bulanan_dikonversi_ke_harian(monkeypatch):
    import math

    import numpy as np

    from app.services.reorder_service import z_from_service_level

    values = [300, 360, 240, 300]  # Jan–Apr → median selisih 31 hari
    svc = _service(
        _run(),
        [_dated_result("p1", values)],
        {"p1": [_bom("p1", "M1", 1)]},
        [_material("M1", "RM-001", lead=7)],
    )

    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]

    days = 31
    mu_d = np.mean(values) / days
    sigma_d = np.std(values, ddof=1) / math.sqrt(days)
    ss = z_from_service_level(95) * sigma_d * math.sqrt(7)
    assert float(r.safety_stock) == pytest.approx(ss, abs=1e-3)
    assert float(r.reorder_point) == pytest.approx(mu_d * 7 + ss, abs=1e-3)
    assert float(r.reorder_point) < np.mean(values)  # bukan μ_bulanan × 7 (≈ 2100)


# ── Buffer stock dari faktor waste pemakaian aktual (Fase 11.1) ──


class FakeUsage:
    def __init__(self, factors):
        self._f = factors

    async def waste_factors(self, material_ids=None):
        return self._f


@pytest.mark.asyncio
async def test_generate_mengisi_buffer_dari_faktor_waste():
    values = [300, 360, 240, 300]
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", values)]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1), _bom("p1", "M2", 1)]}),
        materials=FakeMaterialRepo([_material("M1", "RM-001", lead=7), _material("M2", "RM-002", lead=7)]),
        usage=FakeUsage({"M1": 1.03, "M2": None}),
    )
    recs = {str(r.material_id): r for r in await svc.generate_for_run(USER, "r1", current_stock={"M1": 0, "M2": 0})}

    # buffer = (1.03 − 1) × kebutuhan periode rata-rata (300) = 9
    assert float(recs["M1"].buffer_stock) == pytest.approx(9.0)
    assert float(recs["M1"].waste_factor) == pytest.approx(1.03)
    assert float(recs["M2"].buffer_stock) == 0  # belum ada data pemakaian
    assert recs["M2"].waste_factor is None
    assert float(recs["M1"].reorder_point) == pytest.approx(float(recs["M2"].reorder_point) + 9.0)


@pytest.mark.asyncio
async def test_generate_tanpa_usage_buffer_nol():
    svc = _service(_run(), [_result("p1", [10, 12, 11, 9])], {"p1": [_bom("p1", "M1", 1)]}, [_material("M1", "RM-001")])
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    assert float(r.buffer_stock) == 0


# ── EOQ klasik per material + service level dari master data (Fase 11.4) ──


class FakePlanningSettings:
    def __init__(self, eoq_method="classic", service_level_pct=95.0):
        self._m, self._sl = eoq_method, service_level_pct

    async def eoq_method(self):
        return self._m

    async def service_level_pct(self):
        return self._sl


def _priced(mid, code, price, lead=7):
    m = _material(mid, code, lead=lead)
    m.unit_price = price
    return m


def _tpl_rate(S, H, rate):
    t = _template(S, H)
    t.holding_cost_rate_pct = rate
    return t


@pytest.mark.asyncio
async def test_eoq_klasik_dipakai_bila_harga_dan_rate_ada():
    import math

    values = [900, 1000, 1100]  # bulanan → A = 12.000
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", values)]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1), _bom("p1", "M2", 1)]}),
        materials=FakeMaterialRepo([_priced("M1", "CAP", Decimal("1500")), _material("M2", "BTL")]),
        cost_templates=FakeCostTemplateRepo(_tpl_rate(Decimal("250000"), Decimal("10"), Decimal("20"))),
        settings=FakePlanningSettings("classic"),
    )
    recs = {str(r.material_id): r for r in await svc.generate_for_run(USER, "r1", current_stock={"M1": 0, "M2": 0})}

    m1 = recs["M1"]
    q = math.sqrt(2 * 12_000 * 250_000 / (0.20 * 1_500))
    assert m1.eoq_method == "classic" and m1.item_status == "COMPLETED"
    assert float(m1.annual_demand) == pytest.approx(12_000)
    assert float(m1.unit_price_used) == 1500 and float(m1.holding_rate_used) == pytest.approx(20)
    assert float(m1.total_inventory_cost) == pytest.approx(2 * 12_000 / q * 250_000, rel=1e-4)
    assert float(m1.eoq_qty) == math.ceil(q)  # MOQ 0 → dibulatkan ke atas ke unit utuh

    m2 = recs["M2"]  # tanpa harga → EOQ dinamis, status per item (run tidak gagal)
    assert m2.eoq_method == "dynamic" and m2.item_status == "MISSING_UNIT_PRICE"


@pytest.mark.asyncio
async def test_eoq_klasik_tanpa_rate_template_fallback_dinamis():
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", [900, 1000, 1100])]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([_priced("M1", "CAP", Decimal("1500"))]),
        cost_templates=FakeCostTemplateRepo(_template(Decimal("250000"), Decimal("10"))),
        settings=FakePlanningSettings("classic"),
    )
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    assert r.eoq_method == "dynamic" and r.item_status == "MISSING_HOLDING_RATE"


@pytest.mark.asyncio
async def test_metode_dinamis_dari_master_data():
    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", [900, 1000, 1100])]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([_priced("M1", "CAP", Decimal("1500"))]),
        cost_templates=FakeCostTemplateRepo(_tpl_rate(Decimal("250000"), Decimal("10"), Decimal("20"))),
        settings=FakePlanningSettings("dynamic"),
    )
    r = (await svc.generate_for_run(USER, "r1", current_stock={"M1": 0}))[0]
    assert r.eoq_method == "dynamic" and r.item_status == "COMPLETED"


@pytest.mark.asyncio
async def test_service_level_dari_master_data():
    def svc(pct):
        return ReorderService(
            reorder_repo=FakeReorderRepo(),
            forecast_repo=FakeForecastRepo(_run(), [_dated_result("p1", [300, 360, 240, 300])]),
            boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
            materials=FakeMaterialRepo([_material("M1", "RM", lead=7)]),
            settings=FakePlanningSettings(service_level_pct=pct),
        )

    ss95 = float((await svc(95).generate_for_run(USER, "r1", current_stock={"M1": 0}))[0].safety_stock)
    ss99 = float((await svc(99).generate_for_run(USER, "r1", current_stock={"M1": 0}))[0].safety_stock)
    assert ss99 == pytest.approx(ss95 * 2.3263 / 1.6449, rel=1e-3)


# ── Stok dari snapshot ERP; current_stock request = fallback (Fase 11.5, revisi #16) ──


class FakeStock:
    def __init__(self, latest):
        self._latest = latest

    async def latest_stock(self, as_of=None):
        return self._latest


@pytest.mark.asyncio
async def test_stok_snapshot_menang_atas_request():
    from datetime import date

    svc = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(_run(), [_result("p1", [10, 12, 11, 9, 10, 11])]),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1), _bom("p1", "M2", 1)]}),
        materials=FakeMaterialRepo([_material("M1", "RM-001"), _material("M2", "RM-002")]),
        stock=FakeStock({"M1": (date(2026, 10, 1), 100000.0)}),
    )
    recs = {str(r.material_id): r for r in await svc.generate_for_run(USER, "r1", current_stock={"M1": 0, "M2": 0})}

    assert recs["M1"].status == "overstock"  # snapshot 100.000 dipakai, bukan 0 dari request
    assert float(recs["M1"].current_stock_used) == 100000
    assert recs["M1"].stock_source == "snapshot"
    assert recs["M2"].stock_source == "request"  # belum ada snapshot → fallback request
