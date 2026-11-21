"""
Custom exceptions — setiap exception di sini punya `code` yang mengikuti
daftar Error Codes final di AGENTS.md §4 / docs/ARCHITECTURE.md §5.

Jangan expose stack trace atau detail internal ke client (AGENTS.md §10 #4).
Selalu lempar salah satu exception di bawah ini dari service layer, lalu
biarkan exception handler di main.py yang mengubahnya jadi response JSON
standar.
"""

# Code untuk error di luar AppError — dipasang oleh exception handler global di main.py
# (CR v3.5 §1). HTTPException Starlette (404 route, 405 method) memakai `HTTP_<status>`.
VALIDATION_ERROR = "VALIDATION_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"


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


class WarehouseConfigExistsError(AppError):
    """Produk sudah punya WarehouseConfig — satu produk maksimal satu baris kapasitas."""

    status_code = 409
    code = "WAREHOUSE_CONFIG_EXISTS"


class WarehouseCapacityInvalidError(AppError):
    """Input pallet/dus tidak lengkap/tidak valid untuk mode & unit produknya (Fase 10)."""

    status_code = 400
    code = "WAREHOUSE_CAPACITY_INVALID"


class CostTemplateNotFoundError(AppError):
    status_code = 404
    code = "COST_TEMPLATE_NOT_FOUND"


class CostTemplateNameExistsError(AppError):
    status_code = 409
    code = "COST_TEMPLATE_NAME_EXISTS"


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


class ExternalVariableNotFoundError(AppError):
    """Fase 11.2b — variabel eksternal tidak ada."""

    status_code = 404
    code = "EXTERNAL_VARIABLE_NOT_FOUND"


class ExternalVariableCodeExistsError(AppError):
    """Fase 11.2b — kode variabel eksternal sudah dipakai."""

    status_code = 409
    code = "EXTERNAL_VARIABLE_CODE_EXISTS"


class BomCycleDetectedError(AppError):
    """Fase 11.3 — komponen material membentuk siklus (A → B → A)."""

    status_code = 422
    code = "BOM_CYCLE_DETECTED"


class MaterialComponentNotFoundError(AppError):
    """Fase 11.3 — baris komponen material (BOM level 2) tidak ada."""

    status_code = 404
    code = "MATERIAL_COMPONENT_NOT_FOUND"


class StockSnapshotNotFoundError(AppError):
    """Fase 11.5 — belum ada snapshot stok (ERP) untuk material/tanggal yang diminta."""

    status_code = 404
    code = "STOCK_SNAPSHOT_NOT_FOUND"


class AuthAccountInactiveError(AppError):
    """CR v3.7 — akun dinonaktifkan admin lewat User Management; kredensial Supabase tetap valid."""

    status_code = 403
    code = "AUTH_ACCOUNT_INACTIVE"


class UserNotFoundError(AppError):
    """CR v3.7 — profil user (tabel `users`) tidak ada."""

    status_code = 404
    code = "USER_NOT_FOUND"


class UserEmailExistsError(AppError):
    """CR v3.7 — email sudah dipakai profil user lain."""

    status_code = 409
    code = "USER_EMAIL_EXISTS"


class UserSelfLockoutError(AppError):
    """CR v3.7 — admin mencoba menurunkan role / menonaktifkan dirinya sendiri."""

    status_code = 422
    code = "USER_SELF_LOCKOUT"
