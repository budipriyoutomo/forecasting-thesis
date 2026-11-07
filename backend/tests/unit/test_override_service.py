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
async def test_list_audit_trail_append_only():
    target = _reorder_target()
    svc = _service({"reorder_recommendation": {"rec1": target}})

    await svc.create(USER, "reorder_recommendation", "rec1", new_value={"q": 100}, reason="a1")
    await svc.create(USER, "reorder_recommendation", "rec1", new_value={"q": 120}, reason="a2")

    trail = await svc.list_for_target("rec1")

    assert len(trail) == 2  # kedua revisi tersimpan, tidak saling menimpa


# ── v3.3 Fase 11.14: override reorder dikaitkan ke (run, material) & dipakai downstream ──
from datetime import datetime, timezone  # noqa: E402

from app.services.override_service import latest_reorder_qty  # noqa: E402


class ContextRepo(FakeOverrideRepo):
    async def list_by_context(self, run_id, material_id=None):
        return sorted(
            (o for o in self.items
             if str(o.run_id) == str(run_id) and (material_id is None or str(o.material_id) == str(material_id))),
            key=lambda o: o.created_at, reverse=True,
        )


def _rec(rid, run="r1", mat="m1"):
    t = _reorder_target(rid)
    t.run_id, t.material_id = run, mat
    return t


@pytest.mark.asyncio
async def test_override_reorder_menyimpan_run_dan_material():
    repo = ContextRepo()
    svc = OverrideService(repo, {"reorder_recommendation": _make_resolver({"rec1": _rec("rec1")})})
    ov = await svc.create(USER, "reorder_recommendation", "rec1", {"recommended_order_qty": 120}, "Kontrak")
    assert (ov.run_id, ov.material_id) == ("r1", "m1")


@pytest.mark.asyncio
async def test_override_forecast_tanpa_konteks_material():
    target = SimpleNamespace(id="f1", run_id="r1", method_used="ma", selection_mode="auto", mase=None,
                             forecast_data=[], metrics=None)
    svc = OverrideService(ContextRepo(), {"forecast_result": _make_resolver({"f1": target})})
    ov = await svc.create(USER, "forecast_result", "f1", {"x": 1}, "alasan")
    assert ov.run_id == "r1" and ov.material_id is None


@pytest.mark.asyncio
async def test_riwayat_per_run_material_bertahan_setelah_regenerate():
    # Rekomendasi lama (rec1) diganti rec2 saat generate ulang — riwayat tetap ketemu via (run, material).
    repo = ContextRepo()
    store = {"rec1": _rec("rec1"), "rec2": _rec("rec2")}
    svc = OverrideService(repo, {"reorder_recommendation": _make_resolver(store)})
    await svc.create(USER, "reorder_recommendation", "rec1", {"recommended_order_qty": 100}, "a")
    await svc.create(USER, "reorder_recommendation", "rec2", {"recommended_order_qty": 150}, "b")
    for i, o in enumerate(repo.items):
        o.created_at = datetime(2026, 11, 1 + i, tzinfo=timezone.utc)
    trail = await svc.list_for_reorder("r1", "m1")
    assert [o.reason for o in trail] == ["b", "a"]


def test_latest_reorder_qty_override_terbaru_per_material():
    def ov(mat, qty, day):
        return SimpleNamespace(material_id=mat, new_value={"recommended_order_qty": qty}, reason=f"r{day}",
                               created_at=datetime(2026, 11, day, tzinfo=timezone.utc))
    rows = [ov("m1", 100, 1), ov("m1", 150, 3), ov("m2", "abc", 2), ov("m2", 80, 1), ov(None, 5, 9)]
    got = latest_reorder_qty(rows)
    assert {m: (q, o.reason) for m, (q, o) in got.items()} == {"m1": (150.0, "r3"), "m2": (80.0, "r1")}
