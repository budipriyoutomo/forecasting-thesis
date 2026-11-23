"""
Swap v3.0 — ForecastRunService berbasis PRODUK jadi (produk-only).

Engine forecasting ASLI dipakai (fixture dense); repo/DB di-mock. Test inti:
tiap produk menghasilkan forecast, mode manual (sukses & UNSUPPORTED),
INSUFFICIENT_DATA per-produk, 1 produk gagal tak menggagalkan run, dan 404 produk.
Hasil run berhenti di level produk — tak ada turunan BOM/material.
"""
import uuid
from types import SimpleNamespace

import pytest

from app.services.forecast_run_service import ForecastRunService
from app.utils.exceptions import (
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


class FakeForecastRepo:
    def __init__(self):
        self.runs = {}
        self.results = []

    async def add_run(self, run):
        self.runs[str(run.id)] = run
        return run

    async def get_run(self, run_id):
        return self.runs.get(str(run_id))

    async def list_runs(self, limit=50):
        # (run, label pembuat), terbaru dulu (urutan insert) — semua user (CR v3.5 §3.4).
        rows = [(r, getattr(r, "created_by", None)) for r in self.runs.values()]
        return list(reversed(rows))[:limit]

    async def save_run(self, run):
        return run

    async def add_results(self, results):
        for r in results:
            if getattr(r, "id", None) is None:
                r.id = uuid.uuid4()  # server_default DB disimulasikan
        self.results.extend(results)
        return len(results)

    async def get_result(self, result_id):
        return next((r for r in self.results if str(r.id) == str(result_id)), None)

    async def list_results(self, run_id):
        return [r for r in self.results if str(r.run_id) == str(run_id)]

    async def list_results_for_product(self, product_id):
        return [r for r in self.results if str(r.product_id) == str(product_id)]


def _product(pid, code):
    return SimpleNamespace(id=pid, code=code)


def _service(products, rows_by_product):
    return ForecastRunService(
        forecast_repo=FakeForecastRepo(),
        products=FakeProductRepo(products),
        demand=FakeDemandRepo(rows_by_product),
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
    # 23 Nov 2026 — sistem memilih metode terbaik; deret metode itu langsung berlaku
    assert results[0].method_used is not None
    assert len(results[0].forecast_data) == 7
    assert results[0].metrics["selection_analysis"]["best_method"] == results[0].method_used
    assert str(results[0].product_id) == "p1"
    assert all(len(c["forecast"]) == 7 for c in results[0].candidates_evaluated)


@pytest.mark.asyncio
async def test_manual_mode_sukses(smooth_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    run, results = await svc.create_run(USER, ["p1"], horizon=7, horizon_unit="days", method="moving_average")

    assert results[0].status == "COMPLETED"
    assert results[0].selection_mode == "manual"
    assert results[0].method_used == "moving_average"
    assert len(results[0].forecast_data) == 7  # metode manual langsung berlaku


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
async def test_get_run_milik_user_lain_bisa_dibaca(smooth_df):
    # CR v3.5 §3.4 Opsi A: semua run terlihat semua role (single-tenant).
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})
    run, _ = await svc.create_run(OTHER, ["p1"], horizon=7, horizon_unit="days", method=None)

    got, _ = await svc.get_run(USER, str(run.id))
    assert str(got.id) == str(run.id)


@pytest.mark.asyncio
async def test_run_produk_only_tanpa_turunan_material(smooth_df):
    """Guard regresi: run berhenti di level produk — tak ada breakdown BOM lagi."""
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    _, results = await svc.create_run(USER, ["p1"], horizon=7, horizon_unit="days", method=None)

    assert all(hasattr(r, "product_id") for r in results)
    assert not hasattr(svc, "list_requirements")
    assert not hasattr(svc, "_build_requirements")


# ── Master data Pengaturan Forecast (Fase 11.2a; tanpa metrik ranking sejak 11.15) ──


class FakeRankingSettings:
    def __init__(self, methods=None):
        from app.services.forecasting.registry import get_enabled_methods

        self.methods = get_enabled_methods(methods)

    async def enabled_methods(self):
        return self.methods

    async def display_metrics(self):
        return getattr(self, "metrics", ["mad", "mfe", "mape"])

    async def engine_options(self):
        from app.services.forecasting.types import EngineOptions

        return self.options if hasattr(self, "options") else EngineOptions()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", [None, "moving_average"])
async def test_run_baru_tidak_mencatat_metrik_ranking(smooth_df, method):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    run, _ = await svc.create_run(USER, ["p1"], horizon=7, method=method)

    assert run.ranking_metric is None  # kolom hanya riwayat run sebelum Fase 11.15


@pytest.mark.asyncio
async def test_run_auto_hanya_metode_aktif_master_data(smooth_df):
    svc = ForecastRunService(
        forecast_repo=FakeForecastRepo(),
        products=FakeProductRepo([_product("p1", "SKU-001")]),
        demand=FakeDemandRepo({"p1": _rows(smooth_df)}),
        settings=FakeRankingSettings(["moving_average", "exponential_smoothing"]),
    )

    _, results = await svc.create_run(USER, ["p1"], horizon=7)

    assert {c["method"] for c in results[0].candidates_evaluated} == {"moving_average", "exponential_smoothing"}


@pytest.mark.asyncio
async def test_run_manual_metode_nonaktif_400(smooth_df):
    svc = ForecastRunService(
        forecast_repo=FakeForecastRepo(),
        products=FakeProductRepo([_product("p1", "SKU-001")]),
        demand=FakeDemandRepo({"p1": _rows(smooth_df)}),
        settings=FakeRankingSettings(["moving_average"]),
    )

    with pytest.raises(UnsupportedForecastMethodError):
        await svc.create_run(USER, ["p1"], horizon=7, method="xgboost")


@pytest.mark.asyncio
async def test_run_meneruskan_opsi_engine_dan_menyimpan_hyperparameters(smooth_df):
    from app.services.forecasting.types import EngineOptions

    settings = FakeRankingSettings(["exponential_smoothing"])
    settings.options = EngineOptions(es_alpha_grid=(0.15,))
    svc = ForecastRunService(
        forecast_repo=FakeForecastRepo(),
        products=FakeProductRepo([_product("p1", "SKU-001")]),
        demand=FakeDemandRepo({"p1": _rows(smooth_df)}),
        settings=settings,
    )

    _, results = await svc.create_run(USER, ["p1"], horizon=7)

    assert results[0].candidates_evaluated[0]["hyperparameters"]["alpha"] == 0.15
    assert results[0].feature_importance is None  # ES bukan ML


class FakeExternal:
    def __init__(self, exog):
        self.exog = exog
        self.asked = []

    async def exog_for_product(self, product_id):
        self.asked.append(str(product_id))
        return self.exog


@pytest.mark.asyncio
async def test_run_meneruskan_variabel_eksternal_aktif_ke_engine_ml():
    import pandas as pd

    idx = pd.date_range("2024-01-01", periods=33, freq="MS")
    rows = [SimpleNamespace(period=str(d.date()), actual=float(10 + i % 5)) for i, d in enumerate(idx[:30])]
    exog = pd.DataFrame({"suhu": [float(i % 4) for i in range(33)]}, index=idx)
    external = FakeExternal(exog)
    svc = ForecastRunService(
        forecast_repo=FakeForecastRepo(),
        products=FakeProductRepo([_product("p1", "SKU-001")]),
        demand=FakeDemandRepo({"p1": rows}),
        settings=FakeRankingSettings(["random_forest"]),
        external=external,
    )

    _, results = await svc.create_run(USER, ["p1"], horizon=3)

    assert external.asked == ["p1"]
    assert results[0].candidates_evaluated[0]["hyperparameters"]["exog_used"] == ["suhu"]


@pytest.mark.asyncio
async def test_list_runs_semua_user_terbaru_dulu():
    # Pemilih run halaman Kedatangan Material; CR v3.5 §3.4 Opsi A — semua run terlihat.
    service = _service([], {})
    repo = service._repo
    for rid, uid in (("r1", "u1"), ("r2", "u2"), ("r3", "u1")):
        repo.runs[rid] = SimpleNamespace(id=rid, user_id=uid)
    assert [r.id for r, _ in await service.list_runs()] == ["r3", "r2", "r1"]


# ── CR v3.6 §7.1/§7.2 — histori aktual & alasan gagal disimpan di `metrics` ──
@pytest.mark.asyncio
async def test_hasil_menyimpan_histori_aktual_maks_24(smooth_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    _, results = await svc.create_run(USER, ["p1"], horizon=3, horizon_unit="months", method="moving_average")

    history = results[0].metrics["history"]
    assert len(history) == 24  # fixture 40 baris → 24 terakhir
    assert history[-1] == {"date": str(smooth_df["date"].iloc[-1]), "value": float(smooth_df["quantity"].iloc[-1])}
    assert results[0].metrics["status_reason"] is None
    assert "avg_forecast" in results[0].metrics  # ringkasan lama tetap ada


@pytest.mark.asyncio
async def test_hasil_gagal_menyimpan_alasan(too_short_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(too_short_df)})

    _, results = await svc.create_run(USER, ["p1"], horizon=3, horizon_unit="months", method=None)

    assert "minimal" in results[0].metrics["status_reason"]
    assert len(results[0].metrics["history"]) == 5


@pytest.mark.asyncio
async def test_run_auto_kriteria_terbaik_dari_metrik_pengujian_master_data(smooth_df):
    settings = FakeRankingSettings(["moving_average", "exponential_smoothing", "xgboost"])
    settings.metrics = ["mad"]
    svc = ForecastRunService(
        forecast_repo=FakeForecastRepo(),
        products=FakeProductRepo([_product("p1", "SKU-001")]),
        demand=FakeDemandRepo({"p1": _rows(smooth_df)}),
        settings=settings,
    )

    _, results = await svc.create_run(USER, ["p1"], horizon=7)

    analysis = results[0].metrics["selection_analysis"]
    assert analysis["criteria"] == ["mad"]
    assert float(results[0].mad) == min(c["mad"] for c in results[0].candidates_evaluated)


@pytest.mark.asyncio
async def test_run_manual_tanpa_analisis_pemilihan(smooth_df):
    svc = _service([_product("p1", "SKU-001")], {"p1": _rows(smooth_df)})

    _, results = await svc.create_run(USER, ["p1"], horizon=7, method="moving_average")

    assert results[0].metrics.get("selection_analysis") is None


@pytest.mark.asyncio
async def test_run_auto_satu_metode_terbaik_global_untuk_semua_produk(smooth_df, erratic_df):
    # 23 Nov 2026 — metode terbaik dipilih dari rata-rata pengujian seluruh produk.
    svc = _service(
        [_product("p1", "SKU-001"), _product("p2", "SKU-002")],
        {"p1": _rows(smooth_df), "p2": _rows(erratic_df)},
    )

    _, results = await svc.create_run(USER, ["p1", "p2"], horizon=7)

    assert results[0].method_used == results[1].method_used
    analysis = results[0].metrics["selection_analysis"]
    assert analysis["scope"] == "global"
    assert analysis["n_products"] == 2
    assert results[1].metrics["selection_analysis"]["best_method"] == analysis["best_method"]
