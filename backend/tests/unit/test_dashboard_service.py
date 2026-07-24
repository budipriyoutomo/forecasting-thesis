"""
Fase 7 — DashboardService (agregasi ringkasan). Repo di-mock.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.dashboard_service import DashboardService

USER = "u1"


class FakeMaterials:
    def __init__(self, n):
        self._items = [SimpleNamespace(id=f"m{i}") for i in range(n)]

    async def list(self):
        return self._items


class FakeForecast:
    def __init__(self, run, results):
        self._run = run
        self._results = results

    async def get_latest_run_for_user(self, user_id):
        return self._run

    async def list_results(self, run_id):
        return self._results


class FakeReorder:
    def __init__(self, recs):
        self._recs = recs

    async def list_by_run(self, run_id):
        return self._recs


class FakeOverride:
    def __init__(self, recent):
        self._recent = recent

    async def list_recent(self, limit=20):
        return self._recent[:limit]


def _result(status="COMPLETED", mase=None):
    return SimpleNamespace(status=status, mase=Decimal(str(mase)) if mase is not None else None)


def _rec(status):
    return SimpleNamespace(status=status)


@pytest.mark.asyncio
async def test_summary_dengan_run_terbaru():
    run = SimpleNamespace(id="r1", status="COMPLETED")
    svc = DashboardService(
        FakeMaterials(3),
        FakeForecast(run, [_result(mase=0.4), _result(mase=0.6), _result(status="INSUFFICIENT_DATA")]),
        FakeReorder([_rec("urgent"), _rec("urgent"), _rec("safe")]),
        FakeOverride([object(), object()]),
    )

    summary = await svc.summary(USER)

    assert summary["n_materials"] == 3
    assert summary["latest_run"]["n_completed"] == 2
    assert summary["latest_run"]["n_failed"] == 1
    assert summary["latest_run"]["avg_mase"] == pytest.approx(0.5)
    assert summary["reorder_status_counts"] == {"urgent": 2, "safe": 1, "overstock": 0}
    assert summary["n_recent_overrides"] == 2


@pytest.mark.asyncio
async def test_summary_tanpa_run():
    svc = DashboardService(FakeMaterials(0), FakeForecast(None, []), FakeReorder([]), FakeOverride([]))

    summary = await svc.summary(USER)

    assert summary["n_materials"] == 0
    assert summary["latest_run"] is None
    assert summary["reorder_status_counts"] == {"urgent": 0, "safe": 0, "overstock": 0}


@pytest.mark.asyncio
async def test_summary_run_tanpa_mase_avg_none():
    run = SimpleNamespace(id="r1", status="COMPLETED")
    svc = DashboardService(
        FakeMaterials(1),
        FakeForecast(run, [_result(status="INSUFFICIENT_DATA")]),
        FakeReorder([]),
        FakeOverride([]),
    )

    summary = await svc.summary(USER)

    assert summary["latest_run"]["avg_mase"] is None
