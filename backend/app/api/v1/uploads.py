"""
Endpoint upload demand produk jadi — /api/v1/uploads (Fase 3 v3.0).

POST upload CSV (product_code/period/forecast_existing/planning/actual) → validasi →
simpan permanen + demand_history. GET riwayat & detail. Semua orkestrasi lewat
UploadService (tidak inline). Lihat AGENTS.md §4 (envelope) dan docs/ARCHITECTURE.md §7.
"""
from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import CurrentUser, get_current_user, get_upload_service
from app.schemas.upload import to_upload_response, to_upload_summary
from app.services.upload_service import UploadService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", status_code=201)
async def upload_demand_history(
    file: UploadFile,
    current_user: CurrentUser = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service),
):
    content = await file.read()
    session = await service.create_from_upload(current_user.user_id, file.filename, content)
    return {
        "success": True,
        "data": to_upload_response(session).model_dump(),
        "message": "File berhasil divalidasi dan disimpan",
    }


@router.get("")
async def list_uploads(
    current_user: CurrentUser = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service),
):
    sessions = await service.list_sessions(current_user.user_id)
    return {"success": True, "data": [to_upload_summary(s).model_dump() for s in sessions]}


@router.get("/{session_id}")
async def get_upload(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service),
):
    session = await service.get_session(current_user.user_id, session_id)
    return {"success": True, "data": to_upload_response(session).model_dump()}
