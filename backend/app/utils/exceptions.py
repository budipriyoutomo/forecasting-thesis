"""
Custom exceptions — setiap exception di sini punya `code` yang mengikuti
daftar Error Codes final di AGENTS.md §4 / docs/ARCHITECTURE.md §5.

Jangan expose stack trace atau detail internal ke client (AGENTS.md §10 #4).
Selalu lempar salah satu exception di bawah ini dari service layer, lalu
biarkan exception handler di main.py yang mengubahnya jadi response JSON
standar.
"""


class AppError(Exception):
    """Base class semua error bisnis yang dikenal sistem."""

    status_code: int = 400
    code: str = "APP_ERROR"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AuthTokenMissingOrInvalidError(AppError):
    status_code = 401
    code = "AUTH_INVALID_CREDENTIALS"


class AuthTokenExpiredError(AppError):
    status_code = 401
    code = "AUTH_TOKEN_EXPIRED"


class InvalidCredentialsError(AppError):
    """Login gagal — email/password salah. Kode sama dgn token invalid (AGENTS.md §4)."""

    status_code = 401
    code = "AUTH_INVALID_CREDENTIALS"


class AuthEmailNotVerifiedError(AppError):
    status_code = 403
    code = "AUTH_EMAIL_NOT_VERIFIED"


class ForbiddenRoleError(AppError):
    """Role user tidak diizinkan akses resource (RBAC, FR-8.2)."""

    status_code = 403
    code = "AUTH_FORBIDDEN"


class UploadInvalidFormatError(AppError):
    status_code = 400
    code = "UPLOAD_INVALID_FORMAT"


class UploadFileTooLargeError(AppError):
    status_code = 400
    code = "UPLOAD_FILE_TOO_LARGE"


class InsufficientDataError(AppError):
    status_code = 422
    code = "INSUFFICIENT_DATA"


class MaterialNotFoundError(AppError):
    status_code = 404
    code = "MATERIAL_NOT_FOUND"


class MaterialCodeExistsError(AppError):
    """Kode material sudah dipakai material lain (unik) — konflik saat create/import."""

    status_code = 409
    code = "MATERIAL_CODE_EXISTS"


class ProductNotFoundError(AppError):
    status_code = 404
    code = "PRODUCT_NOT_FOUND"


class ProductCodeExistsError(AppError):
    """Kode produk sudah dipakai produk lain (unik) — konflik saat create/import."""

    status_code = 409
    code = "PRODUCT_CODE_EXISTS"


class BomNotFoundError(AppError):
    """Breakdown material diminta tapi produk belum punya BOM terdaftar (docs §8)."""

    status_code = 404
    code = "BOM_NOT_FOUND"


class WarehouseConfigNotFoundError(AppError):
    status_code = 404
    code = "WAREHOUSE_CONFIG_NOT_FOUND"


# Catatan: WAREHOUSE_CAPACITY_EXCEEDED BUKAN HTTP error — dipakai sebagai flag
# `is_within_capacity=false` di response 200 (docs/ARCHITECTURE.md §5, larangan #17),
# jadi tidak ada exception class untuk itu (keputusan tetap di tangan planner).


class SessionNotFoundError(AppError):
    status_code = 404
    code = "SESSION_NOT_FOUND"


class SessionExpiredError(AppError):
    status_code = 422
    code = "SESSION_EXPIRED"


class StorageUploadFailedError(AppError):
    status_code = 503
    code = "STORAGE_UPLOAD_FAILED"


class OverrideReasonRequiredError(AppError):
    status_code = 400
    code = "OVERRIDE_REASON_REQUIRED"


class OverrideTargetNotFoundError(AppError):
    """Target override (forecast_result/reorder_recommendation) tidak ditemukan."""

    status_code = 404
    code = "OVERRIDE_TARGET_NOT_FOUND"


class ModelSelectionFailedError(AppError):
    status_code = 422
    code = "MODEL_SELECTION_FAILED"


class ForecastRunNotFoundError(AppError):
    status_code = 404
    code = "FORECAST_RUN_NOT_FOUND"


class UnsupportedForecastMethodError(AppError):
    status_code = 400
    code = "UNSUPPORTED_FORECAST_METHOD"
