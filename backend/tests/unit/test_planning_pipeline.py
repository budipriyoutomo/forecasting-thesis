"""
Fase 11.8 — orkestrator alur thesis untuk satu run (REVISI_V2 §1/§3.1):
  [2] MRP: reorder (SS, buffer, EOQ) → [3] proyeksi stok & utilisasi gudang →
  [4] evaluasi inventory (material) → ringkasan biaya.
Tiap tahap tetap service sendiri (bisa dites/dipanggil terpisah); orkestrator hanya
mengurutkan dan merangkum.
"""
from types import SimpleNamespace

import pytest

from app.services.planning_pipeline_service import PlanningPipelineService
from app.utils.exceptions import ForecastRunNotFoundError


class Recorder:
    def __init__(self):
        self.calls = []


def _fakes(rec, fail_on=None):
    class Reorder:
        async def generate_for_run(self, user_id, run_id, current_stock=None):
            rec.calls.append(("reorder", current_stock))
            if fail_on == "reorder":
                raise ForecastRunNotFoundError("x")
            return [SimpleNamespace(status="urgent", item_status="COMPLETED"),
                    SimpleNamespace(status="safe", item_status="MISSING_UNIT_PRICE")]

    class Projection:
        async def generate_for_run(self, user_id, run_id):
            rec.calls.append(("projection",))
            return [
                SimpleNamespace(scenario="proposed", is_within_capacity=True, shortage_qty=0),
                SimpleNamespace(scenario="proposed", is_within_capacity=False, shortage_qty=5),
                SimpleNamespace(scenario="baseline", is_within_capacity=None, shortage_qty=0),
            ]

    class Metrics:
        async def compute_for_run(self, user_id, run_id):
            rec.calls.append(("metrics",))
            return [SimpleNamespace(target_type="material"), SimpleNamespace(target_type="product")]

    class Cost:
        async def get_cost_summary(self, user_id, run_id):
            rec.calls.append(("cost",))
            return SimpleNamespace(total_inventory_cost=1, baseline_inventory_cost=2, savings_pct=50,
                                   shortage_cost=0, baseline_shortage_cost=10, eoq_method="classic")

    return Reorder(), Projection(), Metrics(), Cost()


@pytest.mark.asyncio
async def test_urutan_tahap_dan_ringkasan():
    rec = Recorder()
    svc = PlanningPipelineService(*_fakes(rec))
    out = await svc.run("u1", "r1", current_stock={"m1": 5})

    assert [c[0] for c in rec.calls] == ["reorder", "projection", "metrics", "cost"]
    assert rec.calls[0][1] == {"m1": 5}
    assert out["reorder"] == {"n_materials": 2, "n_urgent": 1, "n_missing_data": 1}
    assert out["projection"] == {"n_rows": 3, "n_over_capacity": 1, "n_shortage_periods": 1, "baseline_available": True}
    assert out["evaluation"] == {"n_material_metrics": 1, "n_product_metrics": 1}
    assert out["cost"]["savings_pct"] == 50 and out["cost"]["eoq_method"] == "classic"


@pytest.mark.asyncio
async def test_gagal_di_tahap_awal_berhenti():
    rec = Recorder()
    svc = PlanningPipelineService(*_fakes(rec, fail_on="reorder"))
    with pytest.raises(ForecastRunNotFoundError):
        await svc.run("u1", "r1")
    assert [c[0] for c in rec.calls] == ["reorder"]


@pytest.mark.asyncio
async def test_endpoint_plan(client, auth_headers):
    from app.api.deps import get_planning_pipeline_service
    from app.main import app

    rec = Recorder()
    app.dependency_overrides[get_planning_pipeline_service] = lambda: PlanningPipelineService(*_fakes(rec))
    try:
        res = await client.post("/api/v1/forecast/runs/r1/plan", json={"current_stock": {"m1": 1}}, headers=auth_headers)
        assert res.status_code == 200, res.text
        assert res.json()["data"]["reorder"]["n_materials"] == 2
        res = await client.post("/api/v1/forecast/runs/r1/plan", headers=auth_headers)
        assert res.status_code == 200
        assert (await client.post("/api/v1/forecast/runs/r1/plan")).status_code == 401
    finally:
        app.dependency_overrides.pop(get_planning_pipeline_service, None)


# ── Fase 11.17 — loop kapasitas gudang ──


class FakeCapacity:
    def __init__(self, rec):
        self._rec = rec

    async def suggest(self, user_id, run_id):
        self._rec.calls.append(("suggest",))
        return {"status": "adjusted", "groups": [{"group": "cap"}], "items": []}


@pytest.mark.asyncio
async def test_overload_menyertakan_usulan_adjust_kapasitas():
    rec = Recorder()
    svc = PlanningPipelineService(*_fakes(rec), capacity=FakeCapacity(rec))
    out = await svc.run("u1", "r1")
    # usulan dihitung setelah proyeksi, sebelum evaluasi
    assert [c[0] for c in rec.calls] == ["reorder", "projection", "suggest", "metrics", "cost"]
    assert out["capacity"]["suggestion"]["status"] == "adjusted"
    assert out["capacity"]["n_adjusted_materials"] == 0


@pytest.mark.asyncio
async def test_muat_kapasitas_tanpa_usulan():
    rec = Recorder()
    reorder, projection, metrics, cost = _fakes(rec)

    class FitProjection:
        async def generate_for_run(self, user_id, run_id):
            return [SimpleNamespace(scenario="proposed", is_within_capacity=True, shortage_qty=0)]

    class AdjustedReorder:
        async def generate_for_run(self, user_id, run_id, current_stock=None):
            return [SimpleNamespace(status="safe", item_status="COMPLETED", adjustment_source="custom"),
                    SimpleNamespace(status="safe", item_status="COMPLETED", adjustment_source=None)]

    svc = PlanningPipelineService(AdjustedReorder(), FitProjection(), metrics, cost, capacity=FakeCapacity(rec))
    out = await svc.run("u1", "r1")
    assert ("suggest",) not in rec.calls
    assert out["capacity"] == {"n_adjusted_materials": 1, "suggestion": None}


@pytest.mark.asyncio
async def test_tanpa_service_kapasitas_usulan_kosong():
    rec = Recorder()
    out = await PlanningPipelineService(*_fakes(rec)).run("u1", "r1")
    assert out["capacity"]["suggestion"] is None
