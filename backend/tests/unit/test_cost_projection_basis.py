"""
28 Nov 2026 (keputusan user) — biaya evaluasi inventory berbasis PROYEKSI STOK:
  biaya pesan  = Σ qty pembelian (order_qty proyeksi) × harga material per unit
  biaya simpan = Σ stok akhir per periode (dus) × tarif H (Rp/dus/bulan)
                 tarif H = (overhead + perawatan + depresiasi aset) / bulan ÷ kapasitas gudang (dus)
                 = "Saran H" di ringkasan template biaya aktif.
Hanya cost-summary (Evaluasi & dashboard); EOQ tetap memakai S/H/i manual template.
Angka diverifikasi manual (AGENTS.md §3).
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.cost_service import (
    CostService,
    holding_cost_from_stock,
    months_per_period,
    ordering_cost_from_orders,
)
from tests.unit.test_cost_service import (
    FakeBomRepo,
    FakeCostTemplateRepo,
    FakeDemandRepo,
    FakeForecastRepo,
    FakeProductRepo,
    FakeReorderRepo,
    _rec,
)

USER = "u1"


# ── Fungsi murni ──


def test_biaya_pesan_qty_pembelian_kali_harga():
    # (0 + 1000 + 0 + 500) × Rp1.500 = Rp2.250.000
    assert ordering_cost_from_orders([0, 1000, 0, 500], 1500) == pytest.approx(2_250_000)


def test_biaya_pesan_tanpa_harga_none():
    assert ordering_cost_from_orders([1000], None) is None
    assert ordering_cost_from_orders([1000], 0) is None


def test_biaya_simpan_stok_akhir_dus_kali_tarif():
    # stok akhir [3000, 6000] pcs, 3000 pcs/dus → 1 + 2 = 3 dus·bulan × Rp2.000 = Rp6.000
    assert holding_cost_from_stock([3000, 6000], 3000, 2000, 1) == pytest.approx(6000)


def test_biaya_simpan_periode_mingguan_diskalakan():
    # 7 hari = 7 ÷ (365/12) bulan
    f = months_per_period(7)
    assert f == pytest.approx(7 / (365 / 12))
    assert holding_cost_from_stock([10], 1, 100, f) == pytest.approx(1000 * f)


def test_months_per_period_bulanan_satu():
    assert months_per_period(31) == 1 and months_per_period(28) == 1


def test_biaya_simpan_tanpa_konversi_atau_tarif_none():
    assert holding_cost_from_stock([100], None, 2000, 1) is None
    assert holding_cost_from_stock([100], 0, 2000, 1) is None
    assert holding_cost_from_stock([100], 10, None, 1) is None


# ── Orkestrasi ──


def _proj(mid, scenario, period, order, ending):
    return SimpleNamespace(material_id=mid, scenario=scenario, period=period, order_qty=order, ending_qty=ending)


class FakeProjections:
    def __init__(self, rows):
        self._rows = rows

    async def list_by_run(self, run_id):
        return self._rows


class FakeMaterials:
    def __init__(self, materials):
        self._by_id = {str(m.id): m for m in materials}

    async def get_by_id(self, mid):
        return self._by_id.get(str(mid))

    async def list(self):
        return list(self._by_id.values())


class FakeWarehouse:
    def __init__(self, configs):
        self._configs = configs

    async def list(self):
        return self._configs


def _overhead(amount):
    return SimpleNamespace(item_type="OVERHEAD", monthly_amount=Decimal(str(amount)), qty=Decimal(1),
                           period_basis="monthly", purchase_price=None, salvage_value=None, useful_life_months=None)


def _template(items):
    return SimpleNamespace(name="T", ordering_cost=Decimal("0"), holding_cost=Decimal("0"),
                           holding_cost_rate_pct=None, items=items)


def _group_config(group, pcs_per_dus, dus_qty):
    return SimpleNamespace(item_type="material_group", material_group=group, capacity_mode="DUS",
                           dus_qty=Decimal(str(dus_qty)), pallet_qty=Decimal(0), dus_per_pallet=None,
                           pcs_per_dus=Decimal(str(pcs_per_dus)) if pcs_per_dus is not None else None)


def _service(projections, materials, configs, template, recs=None):
    run = SimpleNamespace(id="r1", user_id=USER)
    return CostService(
        forecast_repo=FakeForecastRepo(run, []),
        reorder_repo=FakeReorderRepo(recs or []),
        demand_repo=FakeDemandRepo({}),
        boms=FakeBomRepo({}),
        products=FakeProductRepo([]),
        ordering_cost=0,
        holding_cost=0,
        cost_templates=FakeCostTemplateRepo(template),
        materials=FakeMaterials(materials),
        projections=FakeProjections(projections),
        warehouse_configs=FakeWarehouse(configs),
    )


M1 = SimpleNamespace(id="M1", code="M1", category="Cap", unit="PCS", unit_price=Decimal("100"))
M2 = SimpleNamespace(id="M2", code="M2", category="Label", unit="PCS", unit_price=None)


@pytest.mark.asyncio
async def test_cost_summary_berbasis_proyeksi():
    # Template: overhead Rp1.000.000/bulan; kapasitas 500 dus → H = Rp2.000/dus/bulan.
    # M1 (Cap, 100 pcs/dus, Rp100/pcs):
    #   usulan  : order [1000, 0]  → pesan 100.000; stok akhir [500, 200] pcs = 7 dus → simpan 14.000
    #   existing: order [2000, 0]  → pesan 200.000; stok akhir [1500, 1000] pcs = 25 dus → simpan 50.000
    # M2 tanpa harga & tanpa kapasitas grup: dilewati, dihitung.
    rows = [
        _proj("M1", "proposed", "2026-01-01", 1000, 500), _proj("M1", "proposed", "2026-02-01", 0, 200),
        _proj("M1", "baseline", "2026-01-01", 2000, 1500), _proj("M1", "baseline", "2026-02-01", 0, 1000),
        _proj("M2", "proposed", "2026-01-01", 10, 10), _proj("M2", "proposed", "2026-02-01", 0, 5),
    ]
    svc = _service(rows, [M1, M2], [_group_config("cap", 100, 500)], _template([_overhead(1_000_000)]),
                   recs=[_rec("M1", 999, 999, 1998)])
    s = await svc.get_cost_summary(USER, "r1")

    assert s.cost_basis == "projection"
    assert s.holding_rate_per_dus == Decimal("2000")
    assert s.total_ordering_cost == Decimal("100000")
    assert s.total_holding_cost == Decimal("14000")
    assert s.total_inventory_cost == Decimal("114000")
    assert s.baseline_ordering_cost == Decimal("200000")
    assert s.baseline_holding_cost == Decimal("50000")
    assert s.baseline_inventory_cost == Decimal("250000")
    assert float(s.savings_pct) == pytest.approx((250000 - 114000) / 250000 * 100, rel=1e-4)
    assert s.n_materials_without_order_price == 1
    assert s.n_materials_without_capacity == 1

    by_mid = {m.material_id: m for m in s.materials}
    assert by_mid["M1"].ordering_cost == Decimal("100000")
    assert by_mid["M1"].baseline_holding_cost == Decimal("50000")
    assert by_mid["M2"].ordering_cost is None and by_mid["M2"].holding_cost is None


@pytest.mark.asyncio
async def test_unit_dus_tidak_perlu_konversi():
    m = SimpleNamespace(id="M1", code="M1", category="Box", unit="DUS", unit_price=Decimal("10"))
    rows = [_proj("M1", "proposed", "2026-01-01", 5, 4), _proj("M1", "proposed", "2026-02-01", 0, 2)]
    svc = _service(rows, [m], [_group_config("box", None, 100)], _template([_overhead(100_000)]))
    s = await svc.get_cost_summary(USER, "r1")
    # H = 100.000 ÷ 100 dus = 1.000; stok (4 + 2) dus × 1.000 = 6.000
    assert s.total_holding_cost == Decimal("6000")
    assert s.total_ordering_cost == Decimal("50")


@pytest.mark.asyncio
async def test_tanpa_template_aktif_biaya_simpan_nol_tarif_none():
    rows = [_proj("M1", "proposed", "2026-01-01", 1000, 500)]
    svc = _service(rows, [M1], [_group_config("cap", 100, 500)], None)
    s = await svc.get_cost_summary(USER, "r1")
    assert s.cost_basis == "projection"
    assert s.holding_rate_per_dus is None
    assert s.total_holding_cost == Decimal("0")
    assert s.total_ordering_cost == Decimal("100000")


@pytest.mark.asyncio
async def test_belum_ada_proyeksi_fallback_eoq():
    svc = _service([], [M1], [], _template([]), recs=[_rec("M1", 80, 20, 100)])
    s = await svc.get_cost_summary(USER, "r1")
    assert s.cost_basis == "eoq"
    assert s.total_inventory_cost == Decimal("100")
    assert s.materials == []
