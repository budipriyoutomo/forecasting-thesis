"""
Endpoint forecast — /api/v1/forecast (Fase 4), docs/ARCHITECTURE.md §5/§6.8.

POST /forecast/runs   → trigger run banyak produk jadi (mode otomatis / manual).
GET  /forecast/runs/{id} → polling status + hasil.
GET  /forecast/results?product_id=... → riwayat hasil per produk.
POST /forecast/results/{id}/selection → planner memilih metode untuk satu produk (Fase 11.15).
POST /forecast/runs/{id}/selection    → pakai satu metode untuk semua produk di run.

Fase 11.15: mode otomatis tidak memilih pemenang. Hasil dibaca lewat
ForecastSelectionService supaya `method_used`/`forecast` = metode yang berlaku.

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
    get_forecast_selection_service,
    get_forecast_settings_service,
)
from app.services.export_service import ExportService
from app.schemas.forecast import (
    ForecastResultOut,
    ForecastRunRequest,
    ForecastRunSummary,
    MethodSelectionRequest,
    RunSelectionOut,
)
from app.services.forecast_run_service import ForecastRunService
from app.services.forecast_selection_service import (
    PENDING,
    ForecastSelectionService,
    SelectedResult,
)
from app.services.forecast_settings_service import ForecastSettingsService

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/methods", dependencies=[Depends(get_current_user)])
async def list_methods(settings: ForecastSettingsService = Depends(get_forecast_settings_service)):
    """Metode aktif (master data Pengaturan Forecast) untuk MethodSelector di frontend (§6.8)."""
    methods = sorted(await settings.enabled_methods())
    return {"success": True, "data": {"methods": methods}}


def _f(value) -> float | None:
    return float(value) if value is not None else None


def _result_out(result) -> dict:
    return _result_model(result).model_dump()


def _result_model(result) -> ForecastResultOut:
    if not isinstance(result, SelectedResult):
        result = SelectedResult(result)
    selected_at = result.selected_at
    return ForecastResultOut(
        id=str(result.id),
        product_id=str(result.product_id),
        status=result.status,
        method_used=result.method_used,
        selection_status=result.selection_status,
        selection_reason=result.selection_reason,
        selected_at=selected_at.isoformat() if selected_at else None,
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
        feature_importance=getattr(result, "feature_importance", None),
        hyperparameters=getattr(result, "hyperparameters", None),
    )


def _summary(run, results) -> dict:
    results = [r if isinstance(r, SelectedResult) else SelectedResult(r) for r in results]
    n_completed = sum(1 for r in results if r.status == "COMPLETED")
    return ForecastRunSummary(
        run_id=str(run.id),
        status=run.status,
        horizon=run.horizon,
        horizon_unit=run.horizon_unit,
        n_products=len(results),
        n_completed=n_completed,
        n_failed=len(results) - n_completed,
        n_pending_selection=sum(1 for r in results if r.selection_status == PENDING),
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
    selection: ForecastSelectionService = Depends(get_forecast_selection_service),
):
    run, _ = await service.get_run(current_user.user_id, run_id)
    results = await selection.list_results(run_id)
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
    product_id: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
    selection: ForecastSelectionService = Depends(get_forecast_selection_service),
):
    results = await selection.list_results_for_product(product_id)
    return {"success": True, "data": [_result_out(r) for r in results]}


@router.post("/results/{result_id}/selection")
async def select_method(
    result_id: str,
    payload: MethodSelectionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    selection: ForecastSelectionService = Depends(get_forecast_selection_service),
):
    result = await selection.select(current_user.user_id, result_id, payload.method, payload.reason)
    return {"success": True, "data": _result_out(result), "message": "Metode forecast dipilih"}


@router.post("/runs/{run_id}/selection")
async def select_method_for_run(
    run_id: str,
    payload: MethodSelectionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    selection: ForecastSelectionService = Depends(get_forecast_selection_service),
):
    outcome = await selection.select_for_run(current_user.user_id, run_id, payload.method, payload.reason)
    data = RunSelectionOut(
        n_selected=outcome.n_selected,
        skipped_product_ids=outcome.skipped_product_ids,
        results=[_result_model(r) for r in outcome.results],
    ).model_dump()
    return {"success": True, "data": data, "message": f"Metode dipilih untuk {outcome.n_selected} produk"}
