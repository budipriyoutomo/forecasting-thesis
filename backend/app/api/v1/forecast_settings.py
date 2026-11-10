"""
Forecast settings endpoints (Fase 11.2a, 29 Oktober 2026) — docs/ARCHITECTURE.md §5.

GET /forecast-settings → pengaturan aktif (default bila belum pernah disimpan)
PUT /forecast-settings → ubah metrik tampil & metode aktif (admin); berlaku untuk run
                         berikutnya, run lama tetap. Field absen = tidak diubah

RBAC: baca semua role terautentikasi, tulis admin. Logika lewat ForecastSettingsService.
"""
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_current_user, get_forecast_settings_service, require_role
from app.models.forecast_setting import DISPLAY_METRICS
from app.schemas.forecast_settings import ForecastSettingsOut, ForecastSettingsUpdate
from app.services.forecast_settings_service import ForecastSettingsService
from app.services.forecasting import registry
from app.services.forecasting.types import THESIS_ALPHA_GRID

router = APIRouter(prefix="/forecast-settings", tags=["forecast-settings"])


def _to_response(setting) -> dict:
    return ForecastSettingsOut(
        display_metrics=list(getattr(setting, "display_metrics", None) or DISPLAY_METRICS),
        enabled_methods=setting.enabled_methods,
        available_methods=registry.available_methods(),
        es_alpha_grid=[float(a) for a in (setting.es_alpha_grid or THESIS_ALPHA_GRID)],
        es_alpha_metric=setting.es_alpha_metric or "mad",
        ml_grid_search=bool(setting.ml_grid_search),
        ml_winsorize=bool(setting.ml_winsorize),
        service_level_pct=float(setting.service_level_pct or 95),
        eoq_method=setting.eoq_method or "classic",
        rop_formula=getattr(setting, "rop_formula", None) or "with_buffer",
        order_qty_policy=getattr(setting, "order_qty_policy", None) or "order_up_to",
        updated_by=str(setting.updated_by) if setting.updated_by else None,
        updated_at=setting.updated_at,
    ).model_dump(mode="json")


@router.get("", dependencies=[Depends(get_current_user)])
async def get_forecast_settings(service: ForecastSettingsService = Depends(get_forecast_settings_service)):
    return {"success": True, "data": _to_response(await service.get())}


@router.put("")
async def update_forecast_settings(
    payload: ForecastSettingsUpdate,
    current_user: CurrentUser = Depends(require_role("admin")),
    service: ForecastSettingsService = Depends(get_forecast_settings_service),
):
    setting = await service.update(user_id=current_user.user_id, **payload.model_dump())
    return {"success": True, "data": _to_response(setting), "message": "Pengaturan forecast disimpan"}
