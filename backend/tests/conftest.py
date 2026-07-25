"""
Fixtures global — sesuai AGENTS.md §3 / docs/ARCHITECTURE.md §9.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pandas as pd
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

settings = get_settings()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def valid_token() -> str:
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "role": "ppic",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def expired_token() -> str:
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "role": "ppic",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def auth_headers(valid_token) -> dict:
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def expired_auth_headers(expired_token) -> dict:
    return {"Authorization": f"Bearer {expired_token}"}


@pytest.fixture
def valid_csv_bytes() -> bytes:
    # CSV demand produk jadi (v3.0): product_code, period, forecast_existing, planning, actual
    rows = ["product_code,period,forecast_existing,planning,actual"]
    for i in range(12):
        rows.append(f"SKU-{i % 3:03d},2026-0{(i % 6) + 1}-01,{9 + i},{10 + i},{11 + i}")
    return ("\n".join(rows)).encode("utf-8")


@pytest.fixture
def too_few_rows_csv_bytes() -> bytes:
    rows = ["product_code,period,actual", "SKU-001,2026-01-01,10", "SKU-001,2026-02-01,12"]
    return ("\n".join(rows)).encode("utf-8")


@pytest.fixture
def missing_column_csv_bytes() -> bytes:
    # 'actual' hilang → UPLOAD_INVALID_FORMAT
    rows = ["product_code,period"] + [f"SKU-001,2026-01-{i:02d}" for i in range(1, 13)]
    return ("\n".join(rows)).encode("utf-8")


# ── Fixture demand profile — dipakai lintas test classification/engine/service ──
# Dibuat manual (bukan random) supaya deterministik dan jatuh tepat di kuadran
# yang dimaksud (lihat docs/ARCHITECTURE.md §6.2 untuk threshold ADI/CV²).


def _daily_df(quantities: list[float], start: str = "2026-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(quantities), freq="D")
    return pd.DataFrame({"date": dates.astype(str), "quantity": quantities})


def _sparse_df(nonzero_at: list[int], values: list[float], n_days: int, start: str = "2026-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=n_days, freq="D")
    rows = [{"date": str(dates[i].date()), "quantity": v} for i, v in zip(nonzero_at, values)]
    return pd.DataFrame(rows)


@pytest.fixture
def smooth_df() -> pd.DataFrame:
    # Setiap hari ada transaksi (ADI~1), variasi kecil (CV² kecil) → 'smooth'
    quantities = [20 + (i % 3) for i in range(40)]
    return _daily_df(quantities)


@pytest.fixture
def erratic_df() -> pd.DataFrame:
    # Setiap hari ada transaksi (ADI~1), variasi sangat besar (CV² besar) → 'erratic'
    quantities = [90 if i % 2 == 0 else 2 for i in range(40)]
    return _daily_df(quantities)


@pytest.fixture
def intermittent_df() -> pd.DataFrame:
    # Transaksi jarang (ADI besar), nilai konsisten saat terjadi (CV² kecil) → 'intermittent'
    nonzero_at = list(range(0, 40, 5))  # setiap 5 hari
    values = [20.0] * len(nonzero_at)
    return _sparse_df(nonzero_at, values, n_days=40)


@pytest.fixture
def lumpy_df() -> pd.DataFrame:
    # Transaksi jarang (ADI besar) DAN nilai sangat bervariasi (CV² besar) → 'lumpy'
    nonzero_at = list(range(0, 40, 5))
    values = [5.0 if i % 2 == 0 else 60.0 for i in range(len(nonzero_at))]
    return _sparse_df(nonzero_at, values, n_days=40)


@pytest.fixture
def too_short_df() -> pd.DataFrame:
    # Rentang kalender di bawah BACKTEST_MIN_PERIODS (default 12) → INSUFFICIENT_DATA
    return _daily_df([10, 12, 11, 9, 10])
