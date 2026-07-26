"""Fase 7 v3.0 — endpoint cost-summary & inventory-metrics (GET, run-scoped)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import jwt
import pytest

from app.api.deps import get_cost_service, get_inventory_metrics_service
from app.config import get_settings
from app.main import app
from app.services.cost_service import CostService
from app.services.inventory_metrics_service import InventoryMetricsService
from tests.unit.test_cost_service import (
    FakeBomRepo,
    FakeDemandRepo as CostDemandRepo,
    FakeForecastRepo as CostForecastRepo,
    FakeProductRepo as CostProductRepo,
    FakeReorderRepo,
    _demand_row as _cost_demand_row,
    _rec,
)
from tests.unit.test_inventory_metrics_service import (
    FakeDemandRepo as MetricDemandRepo,
    FakeForecastRepo as MetricForecastRepo,
    FakeMetricsRepo,
    FakeProductRepo as MetricProductRepo,
    _demand_row as _metric_demand_row,
    _result,
)

settings = get_settings()
USER_SUB = "00000000-0000-0000-0000-000000000007"
OTHER_SUB = "00000000-0000-0000-0000-000000000008"


def _headers(sub=USER_SUB, role="ppic", expired=False) -> dict:
    exp = datetime.now(timezone.utc) + timedelta(hours=-1 if expired else 1)
    token = jwt.encode({"sub": sub, "role": role, "exp": exp}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_cost_service, None)
    app.dependency_overrides.pop(get_inventory_metrics_service, None)


def _override_cost(run):
    app.dependency_overrides[get_cost_service] = lambda: CostService(
        forecast_repo=CostForecastRepo(run, [SimpleNamespace(product_id="P1", status="COMPLETED", forecast_data=[])]),
        reorder_repo=FakeReorderRepo([_rec("M1", 80, 0, 80)]),
        demand_repo=CostDemandRepo({"P1": [_cost_demand_row("SKU1", f"2026-0{i}-01", 10) for i in (1, 2, 3)]}),
        boms=FakeBomRepo({"P1": [SimpleNamespace(product_id="P1", material_id="M1", qty_per_unit=1)]}),
        products=CostProductRepo([SimpleNamespace(id="P1", code="SKU1")]),
        ordering_cost=100,
        holding_cost=0,
    )


def _override_metrics(run):
    rows = [
        _metric_demand_row("SKU1", "2026-01-01", 10, 10),
        _metric_demand_row("SKU1", "2026-02-01", 10, 8),
        _metric_demand_row("SKU1", "2026-03-01", 10, 10),
    ]
    fdata = [{"date": f"2026-0{i}-01", "value": 9, "lower": 0, "upper": 0} for i in (1, 2, 3)]
    app.dependency_overrides[get_inventory_metrics_service] = lambda: InventoryMetricsService(
        forecast_repo=MetricForecastRepo(run, [_result("P1", fdata)]),
        demand_repo=MetricDemandRepo({"P1": rows}),
        products=MetricProductRepo([SimpleNamespace(id="P1", code="SKU1")]),
        metrics_repo=FakeMetricsRepo(),
    )


@pytest.mark.asyncio
async def test_cost_summary_ok(client):
    _override_cost(SimpleNamespace(id="r1", user_id=USER_SUB))
    res = await client.get("/api/v1/forecast/runs/r1/cost-summary", headers=_headers())
    assert res.status_code == 200
    data = res.json()["data"]
    assert Decimal(data["total_inventory_cost"]) == Decimal("80")
    assert Decimal(data["baseline_inventory_cost"]) == Decimal("100")
    assert Decimal(data["savings_pct"]) == Decimal("20")


@pytest.mark.asyncio
async def test_cost_summary_tanpa_token_401(client):
    _override_cost(SimpleNamespace(id="r1", user_id=USER_SUB))
    res = await client.get("/api/v1/forecast/runs/r1/cost-summary")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_cost_summary_run_milik_user_lain_403(client):
    _override_cost(SimpleNamespace(id="r1", user_id=OTHER_SUB))
    res = await client.get("/api/v1/forecast/runs/r1/cost-summary", headers=_headers())
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "AUTH_FORBIDDEN"


@pytest.mark.asyncio
async def test_inventory_metrics_ok(client):
    _override_metrics(SimpleNamespace(id="r1", user_id=USER_SUB))
    res = await client.get("/api/v1/forecast/runs/r1/inventory-metrics", headers=_headers())
    assert res.status_code == 200
    data = res.json()["data"]
    assert {m["scope"] for m in data} == {"baseline", "forecastiq"}


@pytest.mark.asyncio
async def test_inventory_metrics_run_tidak_ada_404(client):
    _override_metrics(SimpleNamespace(id="r1", user_id=USER_SUB))
    res = await client.get("/api/v1/forecast/runs/ghost/inventory-metrics", headers=_headers())
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "FORECAST_RUN_NOT_FOUND"
