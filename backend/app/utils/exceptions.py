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


class SessionNotFoundError(AppError):
    status_code = 404
    code = "SESSION_NOT_FOUND"


class SessionExpiredError(AppError):
    status_code = 422
    code = "SESSION_EXPIRED"


class OverrideReasonRequiredError(AppError):
    status_code = 400
    code = "OVERRIDE_REASON_REQUIRED"


class ModelSelectionFailedError(AppError):
    status_code = 422
    code = "MODEL_SELECTION_FAILED"


class UnsupportedForecastMethodError(AppError):
    status_code = 400
    code = "UNSUPPORTED_FORECAST_METHOD"
