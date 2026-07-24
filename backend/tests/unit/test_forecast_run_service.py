"""
Fase 4 — ForecastRunService (orkestrasi run banyak material). Engine forecasting
ASLI dipakai (dengan fixture per kuadran); repo/DB di-mock.

Test inti (prioritas tertinggi, AGENTS.md §3): tiap kuadran menghasilkan
forecast, mode manual (sukses & UNSUPPORTED), MODEL_SELECTION_FAILED,
INSUFFICIENT_DATA, 1 material gagal tidak menggagalkan run, 404 material.
"""
from types import SimpleNamespace

import pytest

from app.services.forecast_run_service import ForecastRunService
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    MaterialNotFoundError,
    UnsupportedForecastMethodError,
)

USER = "00000000-0000-0000-0000-000000000001"
OTHER = "00000000-0000-0000-0000-000000000002"


def _rows(df):
    return [SimpleNamespace(date=str(r.date), quantity=float(r.quantity)) for r in df.itertuples()]


class FakeMaterialRepo:
    def __init__(self, materials):
        self._by_id = {m.id: m for m in materials}

    async def get_by_id(self, mid):
        return self._by_id.get(mid)


class FakeConsumptionRepo:
    def __init__(self, rows_by_material):
        self._rows = rows_by_material  # {material_id: [rows]}

    async def list_for_material(self, material_id, material_code):
        return self._rows.get(material_id, [])


class FakeForecastRepo:
    def __init__(self):
        self.runs = {}
        self.results = []

    async def add_run(self, run):
        self.runs[str(run.id)] = run
        return run

    async def get_run(self, run_id):
        return self.runs.get(str(run_id))

    async def save_run(self, run):
        return run

    async def add_results(self, results):
        self.results.extend(results)
        return len(results)

    async def list_results(self, run_id):
        return [r for r in self.results if str(r.run_id) == str(run_id)]

    async def list_results_for_material(self, material_id):
        return [r for r in self.results if str(r.material_id) == str(material_id)]


def _material(mid, code):
    return SimpleNamespace(id=mid, code=code)


def _service(materials, rows_by_material):
    return ForecastRunService(
        forecast_repo=FakeForecastRepo(),
        materials=FakeMaterialRepo(materials),
        consumptions=FakeConsumptionRepo(rows_by_material),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture_name", ["smooth_df", "erratic_df", "intermittent_df", "lumpy_df"])
async def test_auto_setiap_kuadran_menghasilkan_forecast(request, fixture_name):
    df = request.getfixturevalue(fixture_name)
    svc = _service([_material("m1", "RM-001")], {"m1": _rows(df)})

    run, results = await svc.create_run(USER, ["m1"], horizon=7, horizon_unit="days", method=None)

    assert run.status == "COMPLETED"
    assert len(results) == 1
    assert results[0].status == "COMPLETED", f"{fixture_name} harusnya menghasilkan forecast"
    assert results[0].selection_mode == "auto"
    assert results[0].method_used
    assert len(results[0].forecast_data) == 7


@pytest.mark.asyncio
async def test_manual_mode_sukses(smooth_df):
    svc = _service([_material("m1", "RM-001")], {"m1": _rows(smooth_df)})

    run, results = await svc.create_run(USER, ["m1"], horizon=7, horizon_unit="days", method="ets")

    assert results[0].status == "COMPLETED"
    assert results[0].selection_mode == "manual"
    assert results[0].method_used == "ets"


@pytest.mark.asyncio
async def test_manual_mode_metode_tak_dikenal_400(smooth_df):
    svc = _service([_material("m1", "RM-001")], {"m1": _rows(smooth_df)})

    with pytest.raises(UnsupportedForecastMethodError):
        await svc.create_run(USER, ["m1"], horizon=7, horizon_unit="days", method="prophet")


@pytest.mark.asyncio
async def test_insufficient_data_ditandai_per_material(too_short_df):
    svc = _service([_material("m1", "RM-001")], {"m1": _rows(too_short_df)})

    run, results = await svc.create_run(USER, ["m1"], horizon=7, horizon_unit="days", method=None)

    assert run.status == "COMPLETED"  # run tetap selesai
    assert results[0].status == "INSUFFICIENT_DATA"
    assert results[0].forecast_data in (None, [])


@pytest.mark.asyncio
async def test_material_tanpa_data_tidak_menggagalkan_material_lain(smooth_df):
    # m1 punya data (sukses), m2 tidak ada data (INSUFFICIENT_DATA) → run tetap COMPLETED
    svc = _service(
        [_material("m1", "RM-001"), _material("m2", "RM-002")],
        {"m1": _rows(smooth_df), "m2": []},
    )

    run, results = await svc.create_run(USER, ["m1", "m2"], horizon=7, horizon_unit="days", method=None)

    assert run.status == "COMPLETED"
    by_material = {str(r.material_id): r.status for r in results}
    assert by_material["m1"] == "COMPLETED"
    assert by_material["m2"] == "INSUFFICIENT_DATA"


@pytest.mark.asyncio
async def test_material_tidak_ada_404(smooth_df):
    svc = _service([_material("m1", "RM-001")], {"m1": _rows(smooth_df)})

    with pytest.raises(MaterialNotFoundError):
        await svc.create_run(USER, ["m1", "tidak-ada"], horizon=7, horizon_unit="days", method=None)


@pytest.mark.asyncio
async def test_get_run_status(smooth_df):
    svc = _service([_material("m1", "RM-001")], {"m1": _rows(smooth_df)})
    run, _ = await svc.create_run(USER, ["m1"], horizon=7, horizon_unit="days", method=None)

    summary, results = await svc.get_run(USER, str(run.id))

    assert summary.status == "COMPLETED"
    assert len(results) == 1


@pytest.mark.asyncio
async def test_get_run_tidak_ada_404(smooth_df):
    svc = _service([_material("m1", "RM-001")], {"m1": _rows(smooth_df)})

    with pytest.raises(ForecastRunNotFoundError):
        await svc.get_run(USER, "tidak-ada")


@pytest.mark.asyncio
async def test_get_run_milik_user_lain_403(smooth_df):
    svc = _service([_material("m1", "RM-001")], {"m1": _rows(smooth_df)})
    run, _ = await svc.create_run(OTHER, ["m1"], horizon=7, horizon_unit="days", method=None)

    with pytest.raises(ForbiddenRoleError):
        await svc.get_run(USER, str(run.id))
