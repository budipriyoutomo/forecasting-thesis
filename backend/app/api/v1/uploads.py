"""
Endpoint upload — POST /api/v1/uploads

Lihat AGENTS.md §4 (response standard) dan §3 (test wajib per endpoint).
"""
from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import CurrentUser, get_current_user
from app.schemas.upload import UploadResponseData
from app.services import data_ingestion_service

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", status_code=201)
async def upload_consumption_history(
    file: UploadFile,
    current_user: CurrentUser = Depends(get_current_user),
):
    content = await file.read()
    result = data_ingestion_service.parse_and_validate_csv(file.filename, content)

    # Validasi bentuk response lewat schema sebelum dikirim ke client —
    # kalau service berubah tanpa update schema, ini akan langsung gagal
    # saat test/dev, bukan diam-diam mengirim shape yang salah ke frontend.
    validated = UploadResponseData(**result)

    return {
        "success": True,
        "data": validated.model_dump(),
        "message": "File berhasil divalidasi",
    }
