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

    # Login lokal tanpa Supabase Auth — DEVELOPMENT SAJA (app/services/dev_auth.py).
    # Diabaikan kalau ENVIRONMENT != development, jadi aman ikut ter-commit di .env.example.
    DEV_AUTH_ENABLED: bool = False
    DEV_AUTH_PASSWORD: str = "demo1234"  # password bersama user demo hasil seed

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_MIN_ROWS: int = 10  # minimum baris di file agar tidak INSUFFICIENT_DATA saat upload

    # Forecasting engine v3.0 — Comparative Selection (docs/ARCHITECTURE.md §6).
    # Bandingkan seluruh metode aktif via backtest, pilih akurasi terbaik.
    FORECAST_ENGINES_ENABLED: str = "moving_average,exponential_smoothing,random_forest,xgboost,lstm"
    FORECAST_RANKING_METRIC: str = "mape"  # mape | mad | mse | mfe_abs — terendah menang
    COMPUTE_MASE: bool = True  # hitung & simpan MASE tambahan (bukan buat ranking, lihat RECONCILIATION v3.0)
    BACKTEST_MIN_PERIODS: int = 12
    LSTM_MIN_PERIODS: int = 24  # LSTM butuh histori lebih panjang
    MOVING_AVERAGE_WINDOW: int = 3
    ENGINE_TIMEOUT_SECONDS: int = 45  # konvensional & tree-based
    LSTM_ENGINE_TIMEOUT_SECONDS: int = 120  # LSTM butuh timeout lebih longgar
    FORECAST_TIMEOUT_SECONDS: int = 180

    # Engine legacy v2.0 (nonaktif default — docs/ARCHITECTURE.md §6.9).
    # Dipakai hanya bila engines legacy diaktifkan kembali di FORECAST_ENGINES_ENABLED.
    SCORING_WEIGHT_MASE: float = 0.6
    SCORING_WEIGHT_GUARDRAIL: float = 0.3
    SCORING_WEIGHT_FIT: float = 0.1

    # Reorder / safety stock (Fase 5). Z = faktor service level (1.65 ≈ 95%).
    SERVICE_LEVEL_Z: float = 1.65

    # EOQ & total cost (Fase 5 v3.0)
    DEFAULT_ORDERING_COST: float = 0.0
    DEFAULT_HOLDING_COST_RATE: float = 0.0

    # Warehouse capacity constraint (Fase 6 v3.0)
    WAREHOUSE_PALLET_NO_RACKING: bool = True  # sesuai batasan masalah thesis

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
