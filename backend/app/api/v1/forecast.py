"""
Endpoint forecast — POST /api/v1/forecast/runs

Catatan scaffold: endpoint ini menerima data historis langsung di body
(`history`) untuk kemudahan demo/testing tanpa perlu DB (Fase 1-3 belum
diwire ke endpoint ini). Begitu `upload_sessions`/`consumption_history`
tersambung ke database (docs/TASK_BREAKDOWN.md Fase 3), endpoint ini akan
diubah untuk mengambil data dari `material_ids` + DB, bukan dari body.
"""
import pandas as pd
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_current_user
from app.schemas.forecast import ForecastRequest, ForecastResponseData
from app.services.forecasting import forecast_service
from app.utils.exceptions import InsufficientDataError, ModelSelectionFailedError

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post("/runs", status_code=201)
async def create_forecast_run(
    payload: ForecastRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    df = pd.DataFrame([{"date": p.date, "quantity": p.quantity} for p in payload.history])

    record = forecast_service.run_forecast_for_material(
        df, payload.horizon, requested_method=payload.method
    )

    if record.status == "INSUFFICIENT_DATA":
        raise InsufficientDataError(
            "Data historis kurang dari periode minimum yang dibutuhkan untuk forecasting"
        )
    if record.status == "MODEL_SELECTION_FAILED":
        raise ModelSelectionFailedError(
            f"Gagal menghasilkan forecast dengan metode '{record.method_used or 'otomatis'}'"
        )

    data = ForecastResponseData(
        status=record.status,
        method_used=record.method_used,
        selection_mode=record.selection_mode,
        demand_class=record.demand_class,
        mase=record.mase,
        explanation=record.explanation,
        forecast=[p.__dict__ for p in (record.forecast or [])],
    )

    return {
        "success": True,
        "data": data.model_dump(),
        "message": "Forecast berhasil dibuat",
    }
