"""
Pydantic schemas untuk endpoint upload — sesuai docs/ARCHITECTURE.md §4/§5.
"""
from pydantic import BaseModel


class UploadResponseData(BaseModel):
    session_id: str
    n_rows: int
    n_products_detected: int
    preview: list[dict]
    warnings: list[str]
    status: str  # "pending" | "validated"


class UploadSessionSummary(BaseModel):
    session_id: str
    file_name: str
    n_rows: int
    n_products_detected: int
    status: str
    created_at: str | None = None


def to_upload_response(session) -> UploadResponseData:
    return UploadResponseData(
        session_id=str(session.id),
        n_rows=session.n_rows,
        n_products_detected=session.n_products_detected,
        preview=list(session.preview_data or []),
        warnings=list(session.warnings or []),
        status=session.status,
    )


def to_upload_summary(session) -> UploadSessionSummary:
    return UploadSessionSummary(
        session_id=str(session.id),
        file_name=session.file_name,
        n_rows=session.n_rows,
        n_products_detected=session.n_products_detected,
        status=session.status,
        created_at=session.created_at.isoformat() if session.created_at else None,
    )


class SuccessResponse(BaseModel):
    success: bool = True
    data: dict | UploadResponseData
    message: str | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
