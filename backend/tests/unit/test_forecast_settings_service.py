"""
Fase 11.2a — master data Pengaturan Forecast (Keputusan #6, docs/REVISI_V2.md §6.1).

Satu baris global (singleton). Metrik ranking pemenang dibaca dari sini, BUKAN env.
Belum ada baris → default `mad` (tidak dipersist sampai admin menyimpan).
"""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.forecast_settings_service import ForecastSettingsService
from app.services.forecasting.registry import MODEL_REGISTRY
from app.utils.exceptions import UnsupportedForecastMethodError

ADMIN = "00000000-0000-0000-0000-000000000001"


class FakeSettingsRepo:
    def __init__(self, row=None):
        self.row = row
        self.saved = 0

    async def get(self):
        return self.row

    async def save(self, row):
        row.updated_at = datetime(2026, 10, 29, tzinfo=timezone.utc)
        self.row = row
        self.saved += 1
        return row


def _factory(**kw):
    return SimpleNamespace(
        **{
            "id": 1,
            "enabled_methods": None,
            "es_alpha_grid": None,
            "es_alpha_metric": "mad",
            "ml_grid_search": False,
            "ml_winsorize": False,
            "service_level_pct": 95.0,
            "eoq_method": "classic",
            "updated_at": None,
            "updated_by": None,
            **kw,
        }
    )


@pytest.mark.asyncio
async def test_get_tanpa_baris_default_mad():
    repo = FakeSettingsRepo()
    s = await ForecastSettingsService(repo, factory=_factory).get()

    assert s.ranking_metric == "mad"
    assert s.updated_at is None
    assert repo.saved == 0  # default tidak dipersist


@pytest.mark.asyncio
async def test_get_baris_tersimpan():
    repo = FakeSettingsRepo(_factory(ranking_metric="mape"))
    s = await ForecastSettingsService(repo, factory=_factory).get()

    assert s.ranking_metric == "mape"


@pytest.mark.asyncio
async def test_update_membuat_baris_pertama():
    repo = FakeSettingsRepo()
    s = await ForecastSettingsService(repo, factory=_factory).update(ranking_metric="mfe_abs", user_id=ADMIN)

    assert s.ranking_metric == "mfe_abs"
    assert str(s.updated_by) == ADMIN
    assert s.updated_at is not None
    assert repo.saved == 1


@pytest.mark.asyncio
async def test_update_mengubah_baris_yang_ada():
    existing = _factory(ranking_metric="mad")
    repo = FakeSettingsRepo(existing)
    s = await ForecastSettingsService(repo, factory=_factory).update(ranking_metric="mape", user_id=ADMIN)

    assert s is existing
    assert existing.ranking_metric == "mape"


@pytest.mark.asyncio
async def test_ranking_metric_helper():
    svc = ForecastSettingsService(FakeSettingsRepo(_factory(ranking_metric="mape")), factory=_factory)
    assert await svc.ranking_metric() == "mape"
    assert await ForecastSettingsService(FakeSettingsRepo(), factory=_factory).ranking_metric() == "mad"


# ── Daftar metode aktif (pindah dari env FORECAST_ENGINES_ENABLED) ──


@pytest.mark.asyncio
async def test_enabled_methods_default_seluruh_registry():
    svc = ForecastSettingsService(FakeSettingsRepo(), factory=_factory)

    assert await svc.enabled_methods() == set(MODEL_REGISTRY)
    assert (await svc.get()).enabled_methods is None


@pytest.mark.asyncio
async def test_enabled_methods_tersimpan():
    svc = ForecastSettingsService(
        FakeSettingsRepo(_factory(ranking_metric="mad", enabled_methods=["moving_average", "xgboost"])),
        factory=_factory,
    )
    assert await svc.enabled_methods() == {"moving_average", "xgboost"}


@pytest.mark.asyncio
async def test_update_enabled_methods_diurutkan_tanpa_duplikat():
    repo = FakeSettingsRepo()
    s = await ForecastSettingsService(repo, factory=_factory).update(
        ranking_metric="mad", user_id=ADMIN, enabled_methods=["xgboost", "moving_average", "xgboost"]
    )
    assert s.enabled_methods == ["moving_average", "xgboost"]


@pytest.mark.asyncio
async def test_update_tanpa_enabled_methods_mempertahankan_nilai_lama():
    existing = _factory(ranking_metric="mad", enabled_methods=["moving_average"])
    svc = ForecastSettingsService(FakeSettingsRepo(existing), factory=_factory)

    await svc.update(ranking_metric="mape", user_id=ADMIN)

    assert existing.enabled_methods == ["moving_average"]


@pytest.mark.asyncio
async def test_update_metode_tak_dikenal_ditolak():
    repo = FakeSettingsRepo()
    with pytest.raises(UnsupportedForecastMethodError):
        await ForecastSettingsService(repo, factory=_factory).update(
            ranking_metric="mad", user_id=ADMIN, enabled_methods=["moving_average", "prophet"]
        )
    assert repo.saved == 0


# ── Opsi engine (Fase 11.2): grid α, metrik α, grid search, winsorize ──


@pytest.mark.asyncio
async def test_engine_options_default_thesis():
    from app.services.forecasting.types import THESIS_ALPHA_GRID

    opts = await ForecastSettingsService(FakeSettingsRepo(), factory=_factory).engine_options()
    assert opts.es_alpha_grid == THESIS_ALPHA_GRID
    assert opts.es_alpha_metric == "mad"
    assert opts.ml_grid_search is False and opts.ml_winsorize is False


@pytest.mark.asyncio
async def test_engine_options_tersimpan():
    row = _factory(ranking_metric="mad", es_alpha_grid=[0.2, 0.8], es_alpha_metric="mape", ml_grid_search=True)
    opts = await ForecastSettingsService(FakeSettingsRepo(row), factory=_factory).engine_options()
    assert opts.es_alpha_grid == (0.2, 0.8)
    assert opts.es_alpha_metric == "mape"
    assert opts.ml_grid_search is True


@pytest.mark.asyncio
async def test_update_opsi_engine():
    repo = FakeSettingsRepo()
    s = await ForecastSettingsService(repo, factory=_factory).update(
        ranking_metric="mad",
        user_id=ADMIN,
        es_alpha_grid=[0.8, 0.2, 0.2],
        es_alpha_metric="mape",
        ml_grid_search=True,
        ml_winsorize=True,
    )
    assert s.es_alpha_grid == [0.2, 0.8]  # terurut, tanpa duplikat
    assert s.es_alpha_metric == "mape"
    assert s.ml_grid_search is True and s.ml_winsorize is True


@pytest.mark.asyncio
async def test_update_tanpa_opsi_engine_mempertahankan_nilai_lama():
    existing = _factory(ranking_metric="mad", es_alpha_grid=[0.5], ml_grid_search=True)
    await ForecastSettingsService(FakeSettingsRepo(existing), factory=_factory).update(
        ranking_metric="mape", user_id=ADMIN
    )
    assert existing.es_alpha_grid == [0.5] and existing.ml_grid_search is True


# ── Perencanaan persediaan (Fase 11.4): service level & metode EOQ ──


@pytest.mark.asyncio
async def test_default_service_level_dan_eoq():
    svc = ForecastSettingsService(FakeSettingsRepo(), factory=_factory)
    assert await svc.service_level_pct() == 95.0
    assert await svc.eoq_method() == "classic"


@pytest.mark.asyncio
async def test_update_service_level_dan_eoq():
    repo = FakeSettingsRepo()
    svc = ForecastSettingsService(repo, factory=_factory)
    await svc.update(ranking_metric="mad", user_id=ADMIN, service_level_pct=99, eoq_method="dynamic")
    assert await svc.service_level_pct() == 99
    assert await svc.eoq_method() == "dynamic"
