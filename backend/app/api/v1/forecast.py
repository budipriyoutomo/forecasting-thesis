"""
Endpoint forecast — /api/v1/forecast (Fase 4), docs/ARCHITECTURE.md §5/§6.8.

POST /forecast/runs   → trigger run banyak material (mode otomatis / manual).
GET  /forecast/runs/{id} → polling status + hasil.
GET  /forecast/results?material_id=... → riwayat hasil per material.

Semua orkestrasi lewat ForecastRunService (yang memanggil forecast_service
sebagai satu-satunya entry point engine — AGENTS.md §5). Endpoint TIDAK
memanggil classification/registry/scoring langsung.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import (
    CurrentUser,
    get_current_user,
    get_export_service,
    get_forecast_run_service,
)
from app.services.export_service import ExportService
from app.schemas.forecast import (
    ForecastResultOut,
    ForecastRunRequest,
    ForecastRunSummary,
)
from app.services.forecast_run_service import ForecastRunService
from app.services.forecasting import registry

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/methods", dependencies=[Depends(get_current_user)])
async def list_methods():
    """Metode aktif untuk MethodSelector di frontend (§6.8). Listing saja,
    bukan menjalankan seleksi — jadi boleh baca registry langsung."""
    methods = sorted(registry.get_enabled_methods())
    return {"success": True, "data": {"methods": methods}}


def _result_out(result) -> dict:
    profile = result.data_profile or {}
    return ForecastResultOut(
        material_id=str(result.material_id),
        status=result.status,
        method_used=result.method_used,
        selection_mode=result.selection_mode,
        demand_class=profile.get("demand_class"),
        mase=float(result.mase) if result.mase is not None else None,
        explanation=result.explanation,
        forecast=list(result.forecast_data or []),
        metrics=result.metrics,
    ).model_dump()


def _summary(run, results) -> dict:
    n_completed = sum(1 for r in results if r.status == "COMPLETED")
    return ForecastRunSummary(
        run_id=str(run.id),
        status=run.status,
        horizon=run.horizon,
        horizon_unit=run.horizon_unit,
        n_materials=len(results),
        n_completed=n_completed,
        n_failed=len(results) - n_completed,
    ).model_dump()


@router.post("/runs", status_code=201)
async def create_forecast_run(
    payload: ForecastRunRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ForecastRunService = Depends(get_forecast_run_service),
):
    run, results = await service.create_run(
        current_user.user_id,
        payload.material_ids,
        payload.horizon,
        payload.horizon_unit,
        payload.method,
    )
    return {
        "success": True,
        "data": {"run": _summary(run, results), "results": [_result_out(r) for r in results]},
        "message": "Forecast run selesai",
    }


@router.get("/runs/{run_id}")
async def get_forecast_run(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: ForecastRunService = Depends(get_forecast_run_service),
):
    run, results = await service.get_run(current_user.user_id, run_id)
    return {
        "success": True,
        "data": {"run": _summary(run, results), "results": [_result_out(r) for r in results]},
    }


@router.get("/runs/{run_id}/export")
async def export_forecast_run(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: ExportService = Depends(get_export_service),
):
    content, filename, mime = await service.export_forecast(current_user.user_id, run_id)
    return Response(
        content=content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/results")
async def list_results(
    material_id: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: ForecastRunService = Depends(get_forecast_run_service),
):
    results = await service.get_results_for_material(material_id)
    return {"success": True, "data": [_result_out(r) for r in results]}
