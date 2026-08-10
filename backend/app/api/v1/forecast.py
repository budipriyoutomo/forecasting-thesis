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
    MaterialRequirementOut,
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


def _f(value) -> float | None:
    return float(value) if value is not None else None


def _result_out(result) -> dict:
    return ForecastResultOut(
        product_id=str(result.product_id),
        status=result.status,
        method_used=result.method_used,
        selection_mode=result.selection_mode,
        mad=_f(result.mad),
        mfe=_f(result.mfe),
        mse=_f(result.mse),
        mape=_f(result.mape),
        mase=_f(result.mase),
        candidates_evaluated=result.candidates_evaluated,
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
        n_products=len(results),
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
        payload.product_ids,
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


@router.get("/runs/{run_id}/material-requirements")
async def list_material_requirements(
    run_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: ForecastRunService = Depends(get_forecast_run_service),
):
    """Kebutuhan material hasil breakdown BOM per run — dibaca planner sebelum
    override (`target_type="material_requirement"`)."""
    rows = await service.list_requirements(current_user.user_id, run_id)
    return {
        "success": True,
        "data": [
            MaterialRequirementOut(
                id=str(r.id),
                run_id=str(r.run_id),
                material_id=str(r.material_id),
                forecast_qty=r.forecast_qty,
                standard_usage_qty=r.standard_usage_qty,
                actual_usage_qty=r.actual_usage_qty,
                buffer_stock_pct=r.buffer_stock_pct,
            ).model_dump(mode="json")
            for r in rows
        ],
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
    product_id: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: ForecastRunService = Depends(get_forecast_run_service),
):
    results = await service.get_results_for_product(product_id)
    return {"success": True, "data": [_result_out(r) for r in results]}
