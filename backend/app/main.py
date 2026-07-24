"""
FastAPI entry point — ForecastIQ backend.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import auth, forecast, materials, overrides, reorder, uploads
from app.config import get_settings
from app.utils.exceptions import AppError

API_VERSION = "0.1.0"

settings = get_settings()

app = FastAPI(title="ForecastIQ API", version=API_VERSION)

# CORS untuk frontend Next.js. Origin dibaca dari env — di production diisi
# domain Vercel saja (hardening CORS: docs/TASK_BREAKDOWN.md Fase 9).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(materials.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(forecast.router, prefix="/api/v1")
app.include_router(reorder.router, prefix="/api/v1")
app.include_router(overrides.router, prefix="/api/v1")


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


@app.get("/health")
async def health_check():
    """Uptime check — tanpa auth, dipakai monitoring & verifikasi koneksi frontend."""
    return {
        "success": True,
        "data": {"status": "ok", "version": API_VERSION, "environment": settings.ENVIRONMENT},
    }
