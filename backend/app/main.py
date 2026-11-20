"""
FastAPI entry point — ForecastIQ backend.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    auth,
    boms,
    capacity_adjustments,
    cost_templates,
    dashboard,
    external_variables,
    forecast,
    forecast_settings,
    inventory,
    material_usage,
    material_components,
    materials,
    metrics,
    overrides,
    planning,
    products,
    reorder,
    stock_projection,
    uploads,
    warehouse,
)
from app.config import get_settings
from app.utils.exceptions import INTERNAL_ERROR, VALIDATION_ERROR, AppError

API_VERSION = "0.1.0"

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title="ForecastIQ API", version=API_VERSION)

# CORS untuk frontend Next.js. Origin dibaca dari env — di production diisi
# domain publik saja (hardening CORS: docs/TASK_BREAKDOWN.md Fase 9). Di deployment
# VPS frontend & backend satu domain di balik Caddy, jadi request-nya same-origin
# dan CORS praktis tak pernah terpakai (docs/ARCHITECTURE.md §10).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(materials.router, prefix="/api/v1")
app.include_router(material_usage.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
# Sebelum boms: /boms/tree harus menang atas /boms/{bom_id}.
app.include_router(material_components.router, prefix="/api/v1")
app.include_router(boms.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(forecast.router, prefix="/api/v1")
app.include_router(reorder.router, prefix="/api/v1")
app.include_router(warehouse.router, prefix="/api/v1")
app.include_router(stock_projection.router, prefix="/api/v1")
app.include_router(planning.router, prefix="/api/v1")
app.include_router(capacity_adjustments.router, prefix="/api/v1")
app.include_router(cost_templates.router, prefix="/api/v1")
app.include_router(forecast_settings.router, prefix="/api/v1")
app.include_router(external_variables.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(overrides.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Konversi semua AppError (dan turunannya) jadi response error standar
    sesuai AGENTS.md §4 — tidak ada stack trace yang di-expose ke client.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "error": {"code": code, "message": message}})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Validasi Pydantic gagal → 422 envelope standar (CR v3.5 §1), bukan `{"detail": [...]}`.

    Pesan error pertama yang dipakai, diprefix nama field-nya (tanpa segmen lokasi
    `body`/`query`/`path`) supaya pesan berbahasa Indonesia dari validator sampai ke user.
    """
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(str(p) for p in first.get("loc", ())[1:])
    msg = str(first.get("msg", "Input tidak valid")).removeprefix("Value error, ")
    return _error(422, VALIDATION_ERROR, f"{field}: {msg}" if field else msg)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """404 route tidak ada, 405 method salah, dsb → envelope dengan code `HTTP_<status>`."""
    response = _error(exc.status_code, f"HTTP_{exc.status_code}", str(exc.detail))
    if exc.headers:
        response.headers.update(exc.headers)
    return response


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Exception tak tertangani → 500 envelope generik; detail hanya ke log server (AGENTS.md §4)."""
    logger.exception("Unhandled error pada %s %s", request.method, request.url.path)
    return _error(500, INTERNAL_ERROR, "Terjadi kesalahan di server.")


@app.get("/health")
async def health_check():
    """Uptime check — tanpa auth, dipakai monitoring & verifikasi koneksi frontend."""
    return {
        "success": True,
        "data": {"status": "ok", "version": API_VERSION, "environment": settings.ENVIRONMENT},
    }
