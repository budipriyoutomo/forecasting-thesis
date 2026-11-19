"""
Fase 11.17 — CapacityAdjustmentService: simulasi usulan (ulang tahap 2→3 di memori),
simpan usulan/custom (append-only), reset.

Data (ReorderService & StockProjectionService ASLI): kebutuhan bulanan [800, 1200, 1000],
lead time 29,5 hari → μ·L = 1000, σ_d·√L = 200; Buffer 50 (waste 1,05); kebijakan
order_up_to + with_buffer → stok akhir periode pesan = ceil ke atas dari S = 2000 + SS + B.
Stok awal 0, satu material M1 di grup "cap".

  service level   SS       S         stok akhir maks
  99              465,27   2515,27   2516
  98              410,75   2460,75   2461
  97              376,16   2426,16   2427
  95              328,97   2378,97   2379
  92,5            287,91   2337,91   2338
  90              256,31   2306,31   2307
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from statistics import NormalDist
from types import SimpleNamespace

import pytest

from app.services.capacity_adjustment_service import CapacityAdjustmentReader, CapacityAdjustmentService
from app.services.reorder_service import ReorderService
from app.services.stock_projection_service import StockProjectionService
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    MaterialNotFoundError,
    OverrideReasonRequiredError,
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
    _run,
    _template,
)
from tests.unit.test_stock_projection_service import Demand, Products, Repo


def _z(pct):
    return NormalDist().inv_cdf(pct / 100)


class AdjRepo:
    def __init__(self):
        self.rows = []
        self._clock = datetime(2026, 11, 19)

    async def add_all(self, rows):
        for row in rows:
            self._clock += timedelta(seconds=1)
            row.created_at = self._clock
            self.rows.append(row)
        return rows

    async def list_by_run(self, run_id):
        return sorted([r for r in self.rows if str(r.run_id) == str(run_id)], key=lambda r: r.created_at, reverse=True)


class GroupConfigs:
    def __init__(self, capacity):
        self._c = capacity

    async def list(self):
        return [SimpleNamespace(item_type="material_group", material_group="cap", capacity_qty=self._c)]


class Opening:
    def __init__(self, qty):
        self._q = qty

    async def latest_stock(self, as_of=None):
        return {"M1": (date(2025, 12, 31), self._q)} if self._q else {}


class NoReceipts:
    async def list(self, material_id=None, date_from=None, date_to=None):
        return []


class GroupMaterials(FakeMaterialRepo):
    async def list(self):
        return list(self._by_id.values())


def _build(capacity, target=99.0, opening=0.0, manual_ss=None, run=None):
    run = run or _run()
    material = _material("M1", "CAP-RED", lead=29.5, manual_ss=manual_ss)
    material.category = "Cap"
    materials = GroupMaterials([material])
    results = [_dated_result("p1", [800, 1200, 1000])]
    adj_repo = AdjRepo()
    reorder_repo = FakeReorderRepo()
    settings = FakePlanningSettings("dynamic", service_level_pct=target)
    reorder = ReorderService(
        reorder_repo=reorder_repo,
        forecast_repo=FakeForecastRepo(run, results),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=materials,
        cost_templates=FakeCostTemplateRepo(_template(Decimal("100"), Decimal("1"))),
        usage=FakeUsage({"M1": 1.05}),
        settings=settings,
        adjustments=CapacityAdjustmentReader(adj_repo),
    )
    projection = StockProjectionService(
        Repo(), FakeForecastRepo(run, results), reorder_repo, FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        Demand([]), Products(), GroupConfigs(capacity), Opening(opening), NoReceipts(),
        reorder_service=reorder, factory=lambda **kw: SimpleNamespace(**kw), materials=materials,
    )
    svc = CapacityAdjustmentService(
        adj_repo, reorder=reorder, projection=projection, settings=settings, materials=materials,
        factory=lambda **kw: SimpleNamespace(**kw),
    )
    return svc, reorder, projection, adj_repo


@pytest.mark.asyncio
async def test_muat_kapasitas_tanpa_usulan():
    svc, reorder, *_ = _build(capacity=3000)
    await reorder.generate_for_run(USER, "r1")
    out = await svc.suggest(USER, "r1")
    assert out["status"] == "within_capacity"
    assert out["groups"] == [] and out["items"] == []


@pytest.mark.asyncio
async def test_usulan_turunkan_service_level_sampai_muat():
    svc, reorder, *_ = _build(capacity=2450)
    await reorder.generate_for_run(USER, "r1")
    out = await svc.suggest(USER, "r1")

    assert out["status"] == "adjusted"
    assert out["target_service_level_pct"] == 99
    assert out["iterations"] == 2  # 99 → 98 (2461, masih lebih) → 97 (2427, muat)
    [group] = out["groups"]
    assert group["group"] == "cap" and group["status"] == "adjusted"
    assert group["service_level_pct"] == 97
    assert group["excess_before"] == pytest.approx(66)  # 2516 − 2450
    assert group["excess_after"] == 0 and group["cause"] is None
    [item] = out["items"]
    assert item["material_id"] == "M1"
    assert item["safety_stock_before"] == pytest.approx(_z(99) * 200, abs=1e-3)
    assert item["safety_stock_after"] == pytest.approx(_z(97) * 200, abs=1e-3)
    assert item["buffer_stock_before"] == item["buffer_stock_after"] == pytest.approx(50)
    assert item["reorder_point_after"] == pytest.approx(1000 + _z(97) * 200 + 50, abs=1e-3)
    assert item["service_level_after"] == pytest.approx(97, abs=1e-3)
    assert item["service_level_pct"] == 97


@pytest.mark.asyncio
async def test_usulan_tidak_disimpan_dan_rekomendasi_tetap():
    svc, reorder, _, adj_repo = _build(capacity=2450)
    before = await reorder.generate_for_run(USER, "r1")
    await svc.suggest(USER, "r1")
    assert adj_repo.rows == []
    stored = await reorder.list_for_run(USER, "r1")
    assert [float(r.safety_stock) for r in stored] == [float(r.safety_stock) for r in before]


@pytest.mark.asyncio
async def test_usulan_potong_buffer_setelah_batas_bawah_service_level():
    svc, reorder, *_ = _build(capacity=2280, target=95.0)
    await reorder.generate_for_run(USER, "r1")
    out = await svc.suggest(USER, "r1")

    assert out["status"] == "adjusted"
    [group] = out["groups"]
    assert group["service_level_pct"] == 90
    [item] = out["items"]
    assert item["safety_stock_after"] == pytest.approx(_z(90) * 200, abs=1e-3)
    assert item["buffer_stock_after"] == pytest.approx(23, abs=1e-3)  # 2307 − 2280 = 27 dipotong dari 50


@pytest.mark.asyncio
async def test_tidak_muat_walau_ss_90_dan_buffer_nol_infeasible_cycle_stock():
    svc, reorder, *_ = _build(capacity=2100)
    await reorder.generate_for_run(USER, "r1")
    out = await svc.suggest(USER, "r1")

    assert out["status"] == "infeasible"
    [group] = out["groups"]
    assert group["status"] == "infeasible" and group["cause"] == "cycle_stock"
    assert group["excess_after"] == pytest.approx(157)  # ceil(2256,31) − 2100
    [item] = out["items"]
    assert item["buffer_stock_after"] == 0


@pytest.mark.asyncio
async def test_infeasible_karena_stok_awal():
    svc, reorder, *_ = _build(capacity=3000, opening=5000)
    await reorder.generate_for_run(USER, "r1")
    out = await svc.suggest(USER, "r1")
    assert out["status"] == "infeasible"
    assert out["groups"][0]["cause"] == "opening_stock"


@pytest.mark.asyncio
async def test_ss_manual_tidak_diturunkan_lewat_service_level_langsung_buffer():
    # SS manual 400 → S = 2450 → stok akhir 2450; kapasitas 2430 → hanya Buffer yang bisa dipotong.
    svc, reorder, *_ = _build(capacity=2430, manual_ss=400)
    await reorder.generate_for_run(USER, "r1")
    out = await svc.suggest(USER, "r1")
    assert out["status"] == "adjusted"
    [item] = out["items"]
    assert item["safety_stock_after"] == pytest.approx(400)
    assert item["service_level_pct"] is None
    assert item["buffer_stock_after"] == pytest.approx(30)


@pytest.mark.asyncio
async def test_terima_usulan_lalu_perencanaan_ulang_memakai_adjust():
    svc, reorder, projection, adj_repo = _build(capacity=2450)
    await reorder.generate_for_run(USER, "r1")
    out = await svc.suggest(USER, "r1")
    items = [
        {"material_id": i["material_id"], "safety_stock": i["safety_stock_after"],
         "buffer_stock": i["buffer_stock_after"], "service_level_pct": i["service_level_pct"]}
        for i in out["items"]
    ]
    saved = await svc.save(USER, "r1", "suggested", items, reason=None)
    assert len(saved) == 1 and saved[0].source == "suggested"
    assert saved[0].reason  # alasan default untuk usulan sistem
    assert float(saved[0].previous_value["safety_stock"]) == pytest.approx(_z(99) * 200, abs=1e-3)

    # Ulang tahap 2 → 3 (loop flowchart)
    rec = (await reorder.generate_for_run(USER, "r1"))[0]
    assert rec.adjustment_source == "suggested"
    assert float(rec.safety_stock) == pytest.approx(_z(97) * 200, abs=1e-3)
    rows = await projection.generate_for_run(USER, "r1")
    assert all(r.is_within_capacity for r in rows if r.scenario == "proposed")
    assert (await svc.suggest(USER, "r1"))["status"] == "adjusted"  # usulan dihitung dari nilai sistem


@pytest.mark.asyncio
async def test_custom_wajib_alasan():
    svc, reorder, *_ = _build(capacity=2450)
    await reorder.generate_for_run(USER, "r1")
    item = {"material_id": "M1", "safety_stock": 300, "buffer_stock": 10, "service_level_pct": None}
    with pytest.raises(OverrideReasonRequiredError):
        await svc.save(USER, "r1", "custom", [item], reason="  ")
    saved = await svc.save(USER, "r1", "custom", [item], reason="Gudang disewa sebagian")
    assert saved[0].source == "custom" and saved[0].reason == "Gudang disewa sebagian"
    active = await svc.list_active(USER, "r1")
    assert [str(a.material_id) for a in active] == ["M1"]


@pytest.mark.asyncio
async def test_simpan_material_di_luar_run_ditolak():
    svc, reorder, *_ = _build(capacity=2450)
    await reorder.generate_for_run(USER, "r1")
    with pytest.raises(MaterialNotFoundError):
        await svc.save(USER, "r1", "custom", [{"material_id": "MX", "safety_stock": 1, "buffer_stock": 1}], "x")


@pytest.mark.asyncio
async def test_reset_kembali_ke_nilai_sistem():
    svc, reorder, _, adj_repo = _build(capacity=2450)
    await reorder.generate_for_run(USER, "r1")
    await svc.save(USER, "r1", "custom", [{"material_id": "M1", "safety_stock": 0, "buffer_stock": 0}], "uji")
    assert await svc.reset(USER, "r1", reason=None) == 1
    assert adj_repo.rows[-1].source == "reset" and adj_repo.rows[-1].reason
    assert await svc.list_active(USER, "r1") == []
    assert await svc.reset(USER, "r1", reason=None) == 0  # tidak ada yang aktif
    rec = (await reorder.generate_for_run(USER, "r1"))[0]
    assert rec.adjustment_source is None


@pytest.mark.asyncio
async def test_akses_run():
    svc, *_ = _build(capacity=2450)
    with pytest.raises(ForecastRunNotFoundError):
        await svc.suggest(USER, "zz")
    other, *_ = _build(capacity=2450, run=_run(user="u2"))
    with pytest.raises(ForbiddenRoleError):
        await other.suggest(USER, "r1")
    with pytest.raises(ForbiddenRoleError):
        await other.save(USER, "r1", "custom", [], "x")
