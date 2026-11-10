"""
Fase 11.15 — planner memilih metode per produk (tanpa pemenang otomatis).

Pilihan = override append-only (`target_type = forecast_result`, `new_value.method_used`,
alasan wajib). Metode berlaku = override terbaru yang metodenya ada di kandidat; tanpa
override → `method_used` hasil (mode manual / run lama). Hilir membaca lewat
`list_results` service ini — hasil belum dipilih tidak punya `forecast_data` (dilewati).
"""
from types import SimpleNamespace

import pytest

from app.services.forecast_selection_service import ForecastSelectionService
from app.services.override_service import OverrideService
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    OverrideReasonRequiredError,
    OverrideTargetNotFoundError,
    UnsupportedForecastMethodError,
)

USER = "00000000-0000-0000-0000-000000000001"
OTHER = "00000000-0000-0000-0000-000000000002"


def _points(base):
    return [
        {"date": f"2026-0{i + 1}-01", "value": base + i, "lower": base + i - 1, "upper": base + i + 1}
        for i in range(3)
    ]


def _cand(method, base, mad=1.0):
    return {
        "method": method,
        "mad": mad,
        "mfe": -0.5,
        "mse": 2.0,
        "mape": 10.0,
        "mase": 0.9,
        "forecast": _points(base),
        "explanation": f"penjelasan {method}",
        "feature_importance": None,
        "hyperparameters": {"m": method},
    }


def _auto_result(rid="r1", pid="p1", run_id="run1"):
    return SimpleNamespace(
        id=rid,
        run_id=run_id,
        product_id=pid,
        status="COMPLETED",
        method_used=None,
        selection_mode="auto",
        candidates_evaluated=[_cand("moving_average", 10), _cand("xgboost", 20, mad=0.5)],
        mad=None, mfe=None, mse=None, mape=None, mase=None,
        explanation="pilih metode",
        forecast_data=None,
        metrics=None,
        feature_importance=None,
        hyperparameters=None,
    )


class FakeForecastRepo:
    def __init__(self, results, runs=None):
        self.results = {str(r.id): r for r in results}
        self.runs = runs or {"run1": SimpleNamespace(id="run1", user_id=USER)}

    async def get_run(self, run_id):
        return self.runs.get(str(run_id))

    async def get_result(self, result_id):
        return self.results.get(str(result_id))

    async def list_results(self, run_id):
        return [r for r in self.results.values() if str(r.run_id) == str(run_id)]


class FakeOverrideRepo:
    def __init__(self):
        self.items = []

    async def add(self, override):
        self.items.append(override)
        return override

    async def list_by_target(self, target_id):
        return [o for o in reversed(self.items) if str(o.target_id) == str(target_id)]

    async def list_by_context(self, run_id, material_id=None):
        return [o for o in reversed(self.items) if str(o.run_id) == str(run_id)]


def _svc(results, runs=None):
    repo = FakeForecastRepo(results, runs)
    overrides = FakeOverrideRepo()
    override_service = OverrideService(overrides, {"forecast_result": repo.get_result})
    return ForecastSelectionService(repo, overrides, override_service), overrides


# ── Hasil hilir sebelum/sesudah dipilih ──


@pytest.mark.asyncio
async def test_auto_belum_dipilih_tanpa_forecast_data():
    svc, _ = _svc([_auto_result()])

    [r] = await svc.list_results("run1")

    assert r.selection_status == "PENDING_SELECTION"
    assert r.method_used is None
    assert r.forecast_data is None
    assert r.status == "COMPLETED"  # status hasil tetap; hilir melewati karena tanpa deret


@pytest.mark.asyncio
async def test_manual_langsung_berlaku():
    manual = _auto_result()
    manual.selection_mode = "manual"
    manual.method_used = "moving_average"
    manual.forecast_data = _points(10)
    manual.candidates_evaluated = [_cand("moving_average", 10)]
    svc, _ = _svc([manual])

    [r] = await svc.list_results("run1")

    assert r.selection_status == "SELECTED"
    assert r.method_used == "moving_average"
    assert r.forecast_data == _points(10)


@pytest.mark.asyncio
async def test_pilih_metode_mengisi_deret_dan_metrik_kandidat():
    original = _auto_result()
    svc, overrides = _svc([original])

    r = await svc.select(USER, "r1", "xgboost", "Pola musiman lebih cocok")

    assert r.selection_status == "SELECTED"
    assert r.method_used == "xgboost"
    assert r.forecast_data == _points(20)
    assert r.mad == 0.5
    assert r.explanation == "penjelasan xgboost"
    assert r.hyperparameters == {"m": "xgboost"}
    assert r.metrics["avg_forecast"] == 21.0
    assert r.selection_reason == "Pola musiman lebih cocok"
    # append-only: hasil asli tidak diubah, pilihan jadi baris override baru
    assert original.method_used is None and original.forecast_data is None
    [ov] = overrides.items
    assert ov.target_type == "forecast_result"
    assert ov.new_value == {"method_used": "xgboost"}
    assert str(ov.run_id) == "run1"

    [listed] = await svc.list_results("run1")
    assert listed.method_used == "xgboost"


@pytest.mark.asyncio
async def test_pilihan_terbaru_yang_berlaku():
    svc, _ = _svc([_auto_result()])
    await svc.select(USER, "r1", "xgboost", "awal")
    await svc.select(USER, "r1", "moving_average", "ganti")

    [r] = await svc.list_results("run1")

    assert r.method_used == "moving_average"
    assert r.selection_reason == "ganti"


@pytest.mark.asyncio
async def test_pilih_metode_di_luar_kandidat_ditolak():
    svc, overrides = _svc([_auto_result()])

    with pytest.raises(UnsupportedForecastMethodError):
        await svc.select(USER, "r1", "lstm", "coba")
    assert overrides.items == []


@pytest.mark.asyncio
async def test_run_lama_tanpa_deret_kandidat_tidak_bisa_ganti_metode():
    old = _auto_result()
    old.method_used = "moving_average"  # pemenang otomatis sebelum Fase 11.15
    old.forecast_data = _points(10)
    old.candidates_evaluated = [{"method": "moving_average", "mad": 1}, {"method": "xgboost", "mad": 2}]
    svc, _ = _svc([old])

    [r] = await svc.list_results("run1")
    assert r.selection_status == "SELECTED" and r.method_used == "moving_average"
    with pytest.raises(UnsupportedForecastMethodError):
        await svc.select(USER, "r1", "xgboost", "ganti")


@pytest.mark.asyncio
async def test_pilih_tanpa_alasan_ditolak():
    svc, _ = _svc([_auto_result()])

    with pytest.raises(OverrideReasonRequiredError):
        await svc.select(USER, "r1", "xgboost", "  ")


@pytest.mark.asyncio
async def test_pilih_hasil_tidak_ada_404():
    svc, _ = _svc([_auto_result()])

    with pytest.raises(OverrideTargetNotFoundError):
        await svc.select(USER, "ghost", "xgboost", "alasan")


@pytest.mark.asyncio
async def test_pilih_hasil_run_milik_user_lain_403():
    svc, _ = _svc([_auto_result()], runs={"run1": SimpleNamespace(id="run1", user_id=OTHER)})

    with pytest.raises(ForbiddenRoleError):
        await svc.select(USER, "r1", "xgboost", "alasan")


@pytest.mark.asyncio
async def test_hasil_gagal_tidak_bisa_dipilih():
    failed = _auto_result()
    failed.status = "INSUFFICIENT_DATA"
    failed.candidates_evaluated = None
    svc, _ = _svc([failed])

    [r] = await svc.list_results("run1")
    assert r.selection_status is None
    with pytest.raises(UnsupportedForecastMethodError):
        await svc.select(USER, "r1", "xgboost", "alasan")


# ── Pilih massal satu run ──


@pytest.mark.asyncio
async def test_pilih_untuk_semua_produk_melewati_yang_tidak_punya_metode():
    r2 = _auto_result("r2", "p2")
    r2.candidates_evaluated = [_cand("moving_average", 5)]
    failed = _auto_result("r3", "p3")
    failed.status = "MODEL_SELECTION_FAILED"
    failed.candidates_evaluated = None
    svc, overrides = _svc([_auto_result(), r2, failed])

    outcome = await svc.select_for_run(USER, "run1", "xgboost", "Standar planner")

    assert outcome.n_selected == 1
    assert outcome.skipped_product_ids == ["p2", "p3"]
    assert len(overrides.items) == 1
    by_pid = {str(r.product_id): r for r in outcome.results}
    assert by_pid["p1"].method_used == "xgboost"
    assert by_pid["p2"].selection_status == "PENDING_SELECTION"


@pytest.mark.asyncio
async def test_pilih_massal_metode_tidak_ada_di_produk_mana_pun():
    svc, overrides = _svc([_auto_result()])

    with pytest.raises(UnsupportedForecastMethodError):
        await svc.select_for_run(USER, "run1", "lstm", "alasan")
    assert overrides.items == []


@pytest.mark.asyncio
async def test_pilih_massal_tanpa_alasan_ditolak():
    svc, overrides = _svc([_auto_result()])

    with pytest.raises(OverrideReasonRequiredError):
        await svc.select_for_run(USER, "run1", "xgboost", "")
    assert overrides.items == []


@pytest.mark.asyncio
async def test_pilih_massal_run_tidak_ada_dan_milik_user_lain():
    svc, _ = _svc([_auto_result()], runs={"run1": SimpleNamespace(id="run1", user_id=OTHER)})

    with pytest.raises(ForecastRunNotFoundError):
        await svc.select_for_run(USER, "ghost", "xgboost", "alasan")
    with pytest.raises(ForbiddenRoleError):
        await svc.select_for_run(USER, "run1", "xgboost", "alasan")


@pytest.mark.asyncio
async def test_atribut_lain_diteruskan_ke_repo():
    svc, _ = _svc([_auto_result()])

    assert (await svc.get_run("run1")).user_id == USER  # adapter hilir: method repo lain tetap ada


# ── Wiring: SEMUA hilir membaca hasil lewat pilihan planner ──


@pytest.mark.parametrize(
    "getter",
    [
        "get_reorder_service",
        "get_stock_projection_service",
        "get_cost_service",
        "get_warehouse_service",
        "get_inventory_metrics_service",
        "get_export_service",
        "get_dashboard_service",
    ],
)
def test_service_hilir_memakai_adapter_pilihan(getter, monkeypatch):
    from unittest.mock import MagicMock

    from app.api import deps

    monkeypatch.setattr(deps, "build_s3_client", MagicMock(), raising=False)
    service = getattr(deps, getter)(MagicMock())

    assert isinstance(service._forecast, ForecastSelectionService)


@pytest.mark.asyncio
async def test_reorder_melewati_produk_yang_metodenya_belum_dipilih():
    """Hasil PENDING_SELECTION tidak punya deret → tidak masuk kebutuhan material."""
    svc, _ = _svc([_auto_result("r1", "p1"), _auto_result("r2", "p2")])
    await svc.select(USER, "r2", "moving_average", "dipakai")

    series = {
        str(r.product_id): r.forecast_data
        for r in await svc.list_results("run1")
        if r.status == "COMPLETED" and r.forecast_data
    }

    assert series == {"p2": _points(10)}
