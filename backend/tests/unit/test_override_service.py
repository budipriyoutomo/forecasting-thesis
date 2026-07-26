"""
Fase 6 — OverrideService (append-only audit trail, AGENTS.md §5 non-negotiable).

Test wajib: happy path, reason kosong (OVERRIDE_REASON_REQUIRED), override TIDAK
menghapus/mengubah data asli, target tidak ada (OVERRIDE_TARGET_NOT_FOUND).
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.override_service import OverrideService
from app.utils.exceptions import OverrideReasonRequiredError, OverrideTargetNotFoundError

USER = "u1"


class FakeOverrideRepo:
    def __init__(self):
        self.items = []

    async def add(self, override):
        self.items.append(override)
        return override

    async def list_by_target(self, target_id):
        return [o for o in self.items if str(o.target_id) == str(target_id)]


def _reorder_target(rid="rec1"):
    return SimpleNamespace(
        id=rid,
        safety_stock=Decimal("6.6"),
        reorder_point=Decimal("46.6"),
        recommended_order_qty=Decimal("87"),
        status="urgent",
    )


def _material_req_target(rid="mr1"):
    return SimpleNamespace(
        id=rid,
        forecast_qty=Decimal("1200"),
        standard_usage_qty=Decimal("1150"),
        actual_usage_qty=Decimal("1180"),
        buffer_stock_pct=Decimal("5"),
    )


def _service(targets_by_type):
    resolvers = {t: _make_resolver(store) for t, store in targets_by_type.items()}
    return OverrideService(FakeOverrideRepo(), resolvers)


def _make_resolver(store):
    async def resolver(target_id):
        return store.get(str(target_id))

    return resolver


@pytest.mark.asyncio
async def test_create_override_happy_path_menyimpan_previous_dan_new():
    target = _reorder_target()
    svc = _service({"reorder_recommendation": {"rec1": target}})

    ov = await svc.create(
        USER, "reorder_recommendation", "rec1",
        new_value={"recommended_order_qty": 120}, reason="Ada rencana produksi tambahan bulan depan",
    )

    assert ov.reason
    assert ov.new_value == {"recommended_order_qty": 120}
    # previous_value = snapshot nilai lama (audit trail)
    assert ov.previous_value["recommended_order_qty"] == "87"
    assert ov.previous_value["status"] == "urgent"


@pytest.mark.asyncio
async def test_create_override_reason_kosong_ditolak():
    svc = _service({"reorder_recommendation": {"rec1": _reorder_target()}})

    with pytest.raises(OverrideReasonRequiredError):
        await svc.create(USER, "reorder_recommendation", "rec1", new_value={"x": 1}, reason="   ")


@pytest.mark.asyncio
async def test_create_override_tidak_mengubah_data_asli():
    target = _reorder_target()
    svc = _service({"reorder_recommendation": {"rec1": target}})

    await svc.create(
        USER, "reorder_recommendation", "rec1",
        new_value={"recommended_order_qty": 120}, reason="alasan valid",
    )

    # data asli TIDAK berubah — override cuma menambah entri baru
    assert target.recommended_order_qty == Decimal("87")
    assert target.status == "urgent"


@pytest.mark.asyncio
async def test_create_override_target_tidak_ada_404():
    svc = _service({"reorder_recommendation": {}})

    with pytest.raises(OverrideTargetNotFoundError):
        await svc.create(USER, "reorder_recommendation", "ghost", new_value={"x": 1}, reason="alasan")


@pytest.mark.asyncio
async def test_create_override_forecast_result_snapshot():
    target = SimpleNamespace(
        id="fr1", method_used="ets", selection_mode="auto", mase=Decimal("0.5"),
        forecast_data=[{"date": "2026-01-01", "value": 10}], metrics={"avg_forecast": 10},
    )
    svc = _service({"forecast_result": {"fr1": target}})

    ov = await svc.create(
        USER, "forecast_result", "fr1",
        new_value={"forecast_data": [{"date": "2026-01-01", "value": 15}]},
        reason="Koreksi manual dari info lapangan",
    )

    assert ov.previous_value["method_used"] == "ets"
    assert ov.previous_value["mase"] == "0.5"


@pytest.mark.asyncio
async def test_create_override_material_requirement_snapshot():
    # Fase 8: target_type baru `material_requirement` (RECONCILIATION §Fase 8).
    target = _material_req_target()
    svc = _service({"material_requirement": {"mr1": target}})

    ov = await svc.create(
        USER, "material_requirement", "mr1",
        new_value={"forecast_qty": 1300}, reason="Koreksi kebutuhan material dari revisi BOM",
    )

    assert ov.previous_value["forecast_qty"] == "1200"
    assert ov.previous_value["standard_usage_qty"] == "1150"
    assert ov.previous_value["buffer_stock_pct"] == "5"
    # data asli TIDAK berubah
    assert target.forecast_qty == Decimal("1200")


@pytest.mark.asyncio
async def test_create_override_material_requirement_target_tidak_ada_404():
    svc = _service({"material_requirement": {}})

    with pytest.raises(OverrideTargetNotFoundError):
        await svc.create(USER, "material_requirement", "ghost", new_value={"x": 1}, reason="alasan valid")


@pytest.mark.asyncio
async def test_list_audit_trail_append_only():
    target = _reorder_target()
    svc = _service({"reorder_recommendation": {"rec1": target}})

    await svc.create(USER, "reorder_recommendation", "rec1", new_value={"q": 100}, reason="a1")
    await svc.create(USER, "reorder_recommendation", "rec1", new_value={"q": 120}, reason="a2")

    trail = await svc.list_for_target("rec1")

    assert len(trail) == 2  # kedua revisi tersimpan, tidak saling menimpa
