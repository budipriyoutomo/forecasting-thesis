"""
Fase 11.9 (v3.3) — sumber tunggal titik pesan & qty pesan.

Untuk satu material dan setting yang sama, titik pesan (ROP) dan qty pesan di
`reorder_recommendations` harus SAMA dengan yang dipakai `stock_projections`
bila stok yang dilihat kedua modul sama (Reorder: stok saat ini; Proyeksi: stok
setelah kedatangan & pemakaian periode t). Diuji untuk seluruh kombinasi setting.
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.reorder_service import ReorderService, order_policy_from_rec
from app.services.stock_projection_service import StockProjectionService
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
    _material,
    _run,
    _template,
)
from tests.unit.test_stock_projection_service import Configs, Demand, Products, Repo

USAGE = [900, 1000, 1100]
CURRENT = 150.0


class NoReceipts:
    async def list(self, material_id=None, date_from=None, date_to=None):
        return []


class OpeningStock:
    """Stok awal proyeksi dibuat = CURRENT + pemakaian periode 1 → pre[1] == CURRENT."""

    async def latest_stock(self, as_of=None):
        return {"M1": (date(2025, 12, 31), CURRENT + USAGE[0])}


class ProjBoms:
    async def list(self, product_id=None):
        return [SimpleNamespace(product_id="p1", material_id="M1", qty_per_unit=1)]


def _results():
    fdata = [{"date": f"2026-{i + 1:02d}-01", "value": v} for i, v in enumerate(USAGE)]
    return [SimpleNamespace(product_id="p1", status="COMPLETED", forecast_data=fdata)]


@pytest.mark.asyncio
@pytest.mark.parametrize("formula", ["standard", "with_buffer"])
@pytest.mark.parametrize("policy", ["eoq", "order_up_to"])
@pytest.mark.parametrize("moq", [0, 700])
async def test_titik_dan_qty_pesan_identik(formula, policy, moq):
    run = _run()
    reorder_repo = FakeReorderRepo()
    reorder = ReorderService(
        reorder_repo=reorder_repo,
        forecast_repo=FakeForecastRepo(run, _results()),
        boms=FakeBomRepo({"p1": [_bom("p1", "M1", 1)]}),
        materials=FakeMaterialRepo([_material("M1", "CAP", lead=7, moq=moq)]),
        cost_templates=FakeCostTemplateRepo(_template(Decimal("250000"), Decimal("10"))),
        usage=FakeUsage({"M1": 1.05}),
        settings=FakePlanningSettings("dynamic", rop_formula=formula, policy=policy),
    )
    rec = (await reorder.generate_for_run(USER, "r1", current_stock={"M1": CURRENT}))[0]
    assert rec.status == "urgent"  # CURRENT di bawah ROP → kedua modul harus memesan

    # 1) Kebijakan yang direkonstruksi dari baris tersimpan = yang dipakai Reorder.
    p = order_policy_from_rec(rec)
    assert p.reorder_point == pytest.approx(float(rec.reorder_point))
    assert p.order_qty(CURRENT) == pytest.approx(float(rec.recommended_order_qty))

    # 2) Proyeksi stok periode 1 (pre == CURRENT) memesan qty yang sama.
    proj = StockProjectionService(
        Repo(), FakeForecastRepo(run, _results()), reorder_repo, ProjBoms(), Demand([]), Products(), Configs(),
        OpeningStock(), NoReceipts(), factory=lambda **kw: SimpleNamespace(**kw),
    )
    rows = [r for r in await proj.generate_for_run(USER, "r1") if r.scenario == "proposed"]
    first = rows[0]
    assert first.opening_qty - first.usage_qty == pytest.approx(CURRENT)
    assert first.order_qty == pytest.approx(float(rec.recommended_order_qty))
