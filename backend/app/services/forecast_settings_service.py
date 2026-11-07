"""
ForecastSettingsService (Fase 11.2a, 29 Oktober 2026) — master data Pengaturan Forecast.

Metrik ranking pemenang Comparative Selection dibaca dari sini, BUKAN env
(Keputusan #6, docs/REVISI_V2.md §6.1). Belum ada baris → default `mad`, tidak
dipersist sampai admin menyimpan. Validasi nilai di schema (Literal) + CHECK DB.

Daftar metode aktif (`enabled_methods`, pengganti env FORECAST_ENGINES_ENABLED): None =
seluruh metode di registry. Nama di luar registry → UNSUPPORTED_FORECAST_METHOD.

Fase 11.2: opsi engine — grid α ES (None = grid thesis), metrik pemilihan α, grid
search ML, cap outlier IQR → `engine_options()` (EngineOptions untuk tiap run).
Fase 11.4: perencanaan persediaan — target service level (%) & metode EOQ.
Fase 11.9: rumus titik pesan (`rop_formula`) & kebijakan qty pesan (`order_qty_policy`) —
satu setting untuk tabel Reorder dan Proyeksi Stok. Default = perilaku sebelum v3.3.
Argumen `update` yang None = nilai lama dipertahankan.
"""
from collections.abc import Callable
from types import SimpleNamespace

from app.models.forecast_setting import ForecastSetting
from app.services.forecasting import registry
from app.services.forecasting.forecast_service import DEFAULT_RANKING_METRIC
from app.services.forecasting.types import THESIS_ALPHA_GRID, EngineOptions
from app.utils.exceptions import UnsupportedForecastMethodError

_DEFAULTS = {
    "ranking_metric": DEFAULT_RANKING_METRIC,
    "enabled_methods": None,
    "es_alpha_grid": None,
    "es_alpha_metric": "mad",
    "ml_grid_search": False,
    "ml_winsorize": False,
    "service_level_pct": 95.0,  # Fase 11.4 — target service level (%), menggantikan env SERVICE_LEVEL_PCT
    "eoq_method": "classic",  # classic √(2AS/iC) thesis | dynamic
    "rop_formula": "with_buffer",  # standard (μ·L + SS) | with_buffer (μ·L + SS + B)
    "order_qty_policy": "order_up_to",  # order_up_to (S − stok) | eoq (n × EOQ)
}


class ForecastSettingsService:
    def __init__(self, repo, factory: Callable[..., object] = ForecastSetting):
        self._repo = repo
        self._factory = factory

    async def get(self):
        row = await self._repo.get()
        if row is not None:
            return row
        return SimpleNamespace(**_DEFAULTS, updated_by=None, updated_at=None)

    async def ranking_metric(self) -> str:
        return (await self.get()).ranking_metric

    async def enabled_methods(self) -> set[str]:
        return registry.get_enabled_methods((await self.get()).enabled_methods)

    async def service_level_pct(self) -> float:
        return float((await self.get()).service_level_pct or _DEFAULTS["service_level_pct"])

    async def eoq_method(self) -> str:
        return (await self.get()).eoq_method or _DEFAULTS["eoq_method"]

    async def rop_formula(self) -> str:
        return (await self.get()).rop_formula or _DEFAULTS["rop_formula"]

    async def order_qty_policy(self) -> str:
        return (await self.get()).order_qty_policy or _DEFAULTS["order_qty_policy"]

    async def engine_options(self) -> EngineOptions:
        s = await self.get()
        return EngineOptions(
            es_alpha_grid=tuple(float(a) for a in s.es_alpha_grid) if s.es_alpha_grid else THESIS_ALPHA_GRID,
            es_alpha_metric=s.es_alpha_metric or "mad",
            ml_grid_search=bool(s.ml_grid_search),
            ml_winsorize=bool(s.ml_winsorize),
        )

    async def update(
        self,
        ranking_metric: str,
        user_id: str,
        enabled_methods: list[str] | None = None,
        es_alpha_grid: list[float] | None = None,
        es_alpha_metric: str | None = None,
        ml_grid_search: bool | None = None,
        ml_winsorize: bool | None = None,
        service_level_pct: float | None = None,
        eoq_method: str | None = None,
        rop_formula: str | None = None,
        order_qty_policy: str | None = None,
    ):
        methods = None
        if enabled_methods is not None:
            unknown = sorted(set(enabled_methods) - set(registry.available_methods()))
            if unknown:
                raise UnsupportedForecastMethodError(f"Metode tidak dikenal: {', '.join(unknown)}.")
            methods = sorted(set(enabled_methods))

        row = await self._repo.get()
        if row is None:
            row = self._factory(id=1, **_DEFAULTS)
        row.ranking_metric = ranking_metric
        changes = {
            "enabled_methods": methods,
            "es_alpha_grid": sorted({float(a) for a in es_alpha_grid}) if es_alpha_grid is not None else None,
            "es_alpha_metric": es_alpha_metric,
            "ml_grid_search": ml_grid_search,
            "ml_winsorize": ml_winsorize,
            "service_level_pct": service_level_pct,
            "eoq_method": eoq_method,
            "rop_formula": rop_formula,
            "order_qty_policy": order_qty_policy,
        }
        for field, value in changes.items():
            if value is not None:
                setattr(row, field, value)
        row.updated_by = user_id
        return await self._repo.save(row)
