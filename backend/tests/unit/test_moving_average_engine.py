"""TDD moving_average engine v3.0 — data bulanan, forecast flat rata-rata window."""
import math

import pandas as pd
import pytest

from app.services.forecasting.engines.moving_average_engine import forecast_moving_average
from app.services.forecasting.types import EngineOptions


def _monthly_df(values):
    dates = pd.date_range("2024-01-01", periods=len(values), freq="MS")
    return pd.DataFrame({"date": dates, "quantity": values})


def test_forecast_konstan_menghasilkan_nilai_konstan():
    df = _monthly_df([100.0] * 24)
    res = forecast_moving_average(df, horizon=3)
    assert len(res.forecast) == 3
    for pt in res.forecast:
        assert pt.value == pytest.approx(100.0)
    assert res.mape == pytest.approx(0.0, abs=1e-6)


def test_metrik_terisi_bukan_nan():
    df = _monthly_df([10, 12, 14, 13, 15, 16, 18, 17, 19, 20, 22, 21, 23, 24, 26, 25, 27, 28])
    res = forecast_moving_average(df, horizon=2)
    for m in (res.mad, res.mfe, res.mse, res.mape):
        assert not math.isnan(m)
    assert res.mase is not None  # COMPUTE_MASE default true


def test_tanggal_forecast_melangkah_bulanan():
    df = _monthly_df([5.0] * 15)
    res = forecast_moving_average(df, horizon=2)
    # data terakhir 2024-03-01 + 15 bulan → langkah bulanan
    assert res.forecast[0].date != res.forecast[1].date
    d0 = pd.Timestamp(res.forecast[0].date)
    d1 = pd.Timestamp(res.forecast[1].date)
    assert 27 <= (d1 - d0).days <= 32  # kira-kira 1 bulan


# ── Window dari master data Pengaturan Forecast (19 Nov 2026), bukan env ──


def test_default_window_3_tanpa_options():
    df = _monthly_df([float(v) for v in range(1, 19)])  # 1..18
    res = forecast_moving_average(df, horizon=2)
    assert res.forecast[0].value == pytest.approx((16 + 17 + 18) / 3)
    assert res.hyperparameters == {"window": 3}


def test_window_dari_options():
    df = _monthly_df([float(v) for v in range(1, 19)])
    res = forecast_moving_average(df, horizon=2, options=EngineOptions(ma_window=6))
    assert res.forecast[0].value == pytest.approx(sum(range(13, 19)) / 6)
    assert res.hyperparameters == {"window": 6}
    assert "window 6" in res.explanation


def test_window_lebih_panjang_dari_data_train_memakai_seluruh_data():
    df = _monthly_df([10.0, 20.0, 30.0, 40.0])
    res = forecast_moving_average(df, horizon=1, options=EngineOptions(ma_window=12))
    assert res.forecast[0].value == pytest.approx(25.0)
