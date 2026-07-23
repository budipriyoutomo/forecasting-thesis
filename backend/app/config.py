"""
Application settings — dibaca dari environment variables.

Lihat AGENTS.md §5 dan docs/ARCHITECTURE.md §6.7 untuk daftar lengkap env var
yang dibutuhkan seiring fase-fase berikutnya (Supabase, Cloudflare R2, dst).
Untuk Fase 0 (scaffold ini), hanya subset minimal yang benar-benar dipakai.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Runtime
    ENVIRONMENT: str = "development"  # development / staging / production
    CORS_ORIGINS: str = "http://localhost:3000"  # dipisah koma; di production isi domain Vercel saja

    # Auth
    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_MIN_ROWS: int = 10  # minimum baris di file agar tidak INSUFFICIENT_DATA saat upload

    # Forecasting engine (dipakai mulai Fase 4)
    FORECAST_ENGINES_ENABLED: str = "ets,arima,lgbm,croston"  # prophet belum diimplementasikan (lihat engines/prophet_engine.py)
    SCORING_WEIGHT_MASE: float = 0.6
    SCORING_WEIGHT_GUARDRAIL: float = 0.3
    SCORING_WEIGHT_FIT: float = 0.1
    BACKTEST_MIN_PERIODS: int = 12
    ENGINE_TIMEOUT_SECONDS: int = 45
    FORECAST_TIMEOUT_SECONDS: int = 120

    # Database (dipakai mulai Fase 1 — belum wajib untuk scaffold ini)
    DATABASE_URL: str | None = None

    # Supabase / Cloudflare R2 (dipakai mulai Fase 1/3)
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    CLOUDFLARE_R2_ACCOUNT_ID: str | None = None
    CLOUDFLARE_R2_ACCESS_KEY: str | None = None
    CLOUDFLARE_R2_SECRET_KEY: str | None = None
    CLOUDFLARE_R2_BUCKET_NAME: str = "forecastiq-bucket"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
