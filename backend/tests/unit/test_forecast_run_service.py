"""
Swap v3.0 — ForecastRunService berbasis PRODUK jadi + breakdown BOM.

Engine forecasting ASLI dipakai (fixture dense); repo/DB di-mock. Test inti:
tiap produk menghasilkan forecast, mode manual (sukses & UNSUPPORTED),
INSUFFICIENT_DATA per-produk, 1 produk gagal tak menggagalkan run, 404 produk,
dan breakdown BOM → material_requirements.
"""
from types import SimpleNamespace

import pytest

from app.services.forecast_run_service import ForecastRunService
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    ProductNotFoundError,
    UnsupportedForecastMethodError,
)

USER = "00000000-0000-0000-0000-000000000001"
OTHER = "00000000-0000-0000-0000-000000000002"


def _rows(df):
    # demand_history rows: .period (dari kolom date fixture) + .actual (dari quantity)
    return [SimpleNamespace(period=str(r.date), actual=float(r.quantity)) for r in df.itertuples()]


class FakeProductRepo:
    def __init__(self, products):
        self._by_id = {str(p.id): p for p in products}

    async def get_by_id(self, pid):
        return self._by_id.get(str(pid))


class FakeDemandRepo:
    def __init__(self, rows_by_product):
        self._rows = rows_by_product  # {product_id: [rows]}

    async def list_for_product(self, product_id, product_code):
        return self._rows.get(product_id, [])


class FakeBomRepo:
    def __init__(self, boms_by_product=None):
        self._by_product = boms_by_product or {}

    async def list(self, product_id=None):
        return self._by_product.get(product_id, [])


class FakeRequirementRepo:
    def __init__(self):
        self.by_run = {}

    async def replace_for_run(self, run_id, rows):
        self.by_run[str(run_id)] = list(rows)
        return len(rows)


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

    async def list_results_for_product(self, product_id):
        return [r for r in self.results if str(r.product_id) == str(product_id)]


def _product(pid, code):
    return SimpleNamespace(id=pid, code=code)


def _bom(pid, mid, qty):
    return SimpleNamespace(product_id=pid, material_id=mid, qty_per_unit=qty)


def _service(products, rows_by_product, boms_by_product=None, requirements=None):
    return ForecastRunService(
        forecast_repo=FakeForecastRepo(),
        products=FakeProductRepo(products),
        demand=FakeDemandRepo(rows_by_product),
        boms=FakeBomRepo(boms_by_product),
        requirements=requirements,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture_name", ["smooth_df", "erratic_df"])
async def test_auto_data_dense_menghasilkan_forecast(request, fixture_name):
    df = request.getfixturevalue(fixture_name)
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(df)})

    run, results = await svc.create_run(USER, ["p1"], horizon=7, horizon_unit="days", method=None)

    assert run.status == "COMPLETED"
    assert len(results) == 1
    assert results[0].status == "COMPLETED", f"{fixture_name} harusnya menghasilkan forecast"
    assert results[0].selection_mode == "auto"
    assert results[0].method_used
    assert str(results[0].product_id) == "p1"
    assert results[0].candidates_evaluated
    assert len(results[0].forecast_data) == 7


@pytest.mark.asyncio
async def test_manual_mode_sukses(smooth_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    run, results = await svc.create_run(USER, ["p1"], horizon=7, horizon_unit="days", method="moving_average")

    assert results[0].status == "COMPLETED"
    assert results[0].selection_mode == "manual"
    assert results[0].method_used == "moving_average"


@pytest.mark.asyncio
async def test_manual_mode_metode_tak_dikenal_400(smooth_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    with pytest.raises(UnsupportedForecastMethodError):
        await svc.create_run(USER, ["p1"], horizon=7, horizon_unit="days", method="prophet")


@pytest.mark.asyncio
async def test_insufficient_data_ditandai_per_produk(too_short_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(too_short_df)})

    run, results = await svc.create_run(USER, ["p1"], horizon=7, horizon_unit="days", method=None)

    assert run.status == "COMPLETED"
    assert results[0].status == "INSUFFICIENT_DATA"
    assert results[0].forecast_data in (None, [])


@pytest.mark.asyncio
async def test_produk_tanpa_data_tidak_menggagalkan_produk_lain(smooth_df):
    svc = _service(
        [_product("p1", "SKU-001"), _product("p2", "SKU-002")],
        {"p1": _rows(smooth_df), "p2": []},
    )

    run, results = await svc.create_run(USER, ["p1", "p2"], horizon=7, horizon_unit="days", method=None)

    assert run.status == "COMPLETED"
    by_product = {str(r.product_id): r.status for r in results}
    assert by_product["p1"] == "COMPLETED"
    assert by_product["p2"] == "INSUFFICIENT_DATA"


@pytest.mark.asyncio
async def test_produk_tidak_ada_404(smooth_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    with pytest.raises(ProductNotFoundError):
        await svc.create_run(USER, ["p1", "ghost"], horizon=7, horizon_unit="days", method=None)


@pytest.mark.asyncio
async def test_breakdown_bom_menghasilkan_material_requirements(smooth_df):
    reqs = FakeRequirementRepo()
    # p1 butuh 2×M1 + 1×M2
    svc = _service(
        [_product("p1", "SKU-001")],
        {"p1": _rows(smooth_df)},
        boms_by_product={"p1": [_bom("p1", "M1", 2), _bom("p1", "M2", 1)]},
        requirements=reqs,
    )

    run, _ = await svc.create_run(USER, ["p1"], horizon=7, horizon_unit="days", method=None)

    persisted = reqs.by_run[str(run.id)]
    by_material = {r.material_id: float(r.forecast_qty) for r in persisted}
    assert set(by_material) == {"M1", "M2"}
    # M1 = 2 × total forecast, M2 = 1 × total forecast → M1 = 2 × M2
    assert by_material["M1"] == pytest.approx(2 * by_material["M2"])


@pytest.mark.asyncio
async def test_get_run_status(smooth_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    run, _ = await svc.create_run(USER, ["p1"], horizon=7, horizon_unit="days", method=None)

    summary, results = await svc.get_run(USER, str(run.id))

    assert summary.status == "COMPLETED"
    assert len(results) == 1


@pytest.mark.asyncio
async def test_get_run_tidak_ada_404(smooth_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    with pytest.raises(ForecastRunNotFoundError):
        await svc.get_run(USER, "tidak-ada")


@pytest.mark.asyncio
async def test_get_run_milik_user_lain_403(smooth_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    run, _ = await svc.create_run(OTHER, ["p1"], horizon=7, horizon_unit="days", method=None)

    with pytest.raises(ForbiddenRoleError):
        await svc.get_run(USER, str(run.id))
