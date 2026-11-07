"""
Swap v3.0 — endpoint /api/v1/reorder. Service di-override (fake), reorder per
material dari breakdown BOM atas forecast produk.
"""
import pytest

from app.api.deps import get_reorder_service
from app.main import app
from app.services.reorder_service import ReorderService
from tests.unit.test_reorder_service import (
    FakeBomRepo,
    FakeForecastRepo,
    FakeMaterialRepo,
    FakeReorderRepo,
    _bom,
    _material,
    _result,
    _run,
)

USER_SUB = "00000000-0000-0000-0000-000000000001"


def _override(run, results, boms_by_product, materials):
    service = ReorderService(
        reorder_repo=FakeReorderRepo(),
        forecast_repo=FakeForecastRepo(run, results),
        boms=FakeBomRepo(boms_by_product),
        materials=FakeMaterialRepo(materials),
    )
    app.dependency_overrides[get_reorder_service] = lambda: service
    return service


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_reorder_service, None)


@pytest.mark.asyncio
async def test_generate_recommendations_201(client, auth_headers):
    _override(
        _run(rid="r1", user=USER_SUB),
        [_result("p1", [10, 12, 11, 9, 10, 11])],
        {"p1": [_bom("p1", "m1", 1)]},
        [_material("m1", "RM-001", lead=4)],
    )

    res = await client.post(
        "/api/v1/reorder/recommendations",
        headers=auth_headers,
        json={"run_id": "r1", "current_stock": {"m1": 0}},
    )

    assert res.status_code == 201
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["status"] in ("urgent", "safe", "overstock")
    assert float(data[0]["reorder_point"]) > 0


@pytest.mark.asyncio
async def test_generate_tanpa_auth_401(client):
    _override(_run(rid="r1", user=USER_SUB), [], {}, [])
    res = await client.post("/api/v1/reorder/recommendations", json={"run_id": "r1"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_generate_run_tidak_ada_404(client, auth_headers):
    _override(None, [], {}, [])
    res = await client.post(
        "/api/v1/reorder/recommendations", headers=auth_headers, json={"run_id": "ghost"}
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "FORECAST_RUN_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_recommendations_filter_status(client, auth_headers):
    service = _override(
        _run(rid="r1", user=USER_SUB),
        [_result("p1", [10, 12, 11, 9, 10, 11])],
        {"p1": [_bom("p1", "m1", 1), _bom("p1", "m2", 1)]},
        [_material("m1", "RM-001"), _material("m2", "RM-002")],
    )
    await service.generate_for_run(USER_SUB, "r1", current_stock={"m1": 0, "m2": 100000})

    res = await client.get(
        "/api/v1/reorder/recommendations?run_id=r1&status=overstock", headers=auth_headers
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert all(r["status"] == "overstock" for r in data)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_generate_menyertakan_kebijakan_pesan(client, auth_headers):
    # Fase 11.9: rumus ROP & kebijakan qty pesan yang dipakai ikut di response (audit).
    _override(
        _run(rid="r1", user=USER_SUB),
        [_result("p1", [10, 12, 11, 9, 10, 11])],
        {"p1": [_bom("p1", "m1", 1)]},
        [_material("m1", "RM-001", lead=4)],
    )
    res = await client.post(
        "/api/v1/reorder/recommendations", headers=auth_headers, json={"run_id": "r1", "current_stock": {"m1": 0}}
    )
    row = res.json()["data"][0]
    assert row["rop_formula_used"] == "with_buffer"
    assert row["order_qty_policy_used"] == "order_up_to"
    assert float(row["order_up_to_level"]) > float(row["reorder_point"])


def test_out_menyertakan_id_untuk_target_override():
    # Override planner butuh id rekomendasi sebagai target_id (UI override, v3.3).
    from decimal import Decimal
    from types import SimpleNamespace

    from app.api.v1.reorder import _out

    rec = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111", material_id="m1", safety_stock=Decimal("1"),
        reorder_point=Decimal("2"), recommended_order_qty=Decimal("3"), status="urgent",
    )
    assert _out(rec)["id"] == "11111111-1111-1111-1111-111111111111"
    rec.id = None  # rekomendasi belum di-flush (fake repo) → null, bukan crash
    assert _out(rec)["id"] is None


def test_out_menyertakan_qty_override_yang_berlaku():
    from datetime import datetime, timezone
    from decimal import Decimal
    from types import SimpleNamespace

    from app.api.v1.reorder import _out

    rec = SimpleNamespace(id="rec-1", material_id="m1", safety_stock=Decimal("1"), reorder_point=Decimal("2"),
                          recommended_order_qty=Decimal("87"), status="urgent")
    ov = SimpleNamespace(reason="Kontrak supplier", created_at=datetime(2026, 11, 7, tzinfo=timezone.utc))
    out = _out(rec, (150.0, ov))
    assert float(out["override_qty"]) == 150 and out["override_reason"] == "Kontrak supplier"
    assert out["override_at"].startswith("2026-11-07")
    assert float(out["recommended_order_qty"]) == 87  # angka sistem tidak berubah
    assert _out(rec)["override_qty"] is None


@pytest.mark.asyncio
async def test_service_override_map_kosong_tanpa_dependency_dan_dari_override_service():
    from tests.unit.test_reorder_service import FakeForecastRepo, _run

    svc = ReorderService(reorder_repo=FakeReorderRepo(), forecast_repo=FakeForecastRepo(_run(), []), boms=None,
                         materials=None)
    assert await svc.override_map("r1") == {}

    class Ovs:
        async def reorder_qty_by_material(self, run_id):
            return {"m1": (150.0, object())}

    svc._overrides = Ovs()
    assert (await svc.override_map("r1"))["m1"][0] == 150.0
