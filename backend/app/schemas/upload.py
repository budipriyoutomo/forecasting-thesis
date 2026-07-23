"""
Pydantic schemas untuk endpoint upload — sesuai docs/ARCHITECTURE.md §4/§5.
"""
from pydantic import BaseModel


class UploadResponseData(BaseModel):
    session_id: str
    n_rows: int
    n_materials_detected: int
    preview: list[dict]
    warnings: list[str]
    status: str  # "pending" | "validated"


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
