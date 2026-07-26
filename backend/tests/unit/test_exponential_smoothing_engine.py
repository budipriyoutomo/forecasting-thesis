"""TDD exponential_smoothing engine v3.0 — SES manual, alpha di-tuning grid."""
import math

import pandas as pd
import pytest

from app.services.forecasting.engines.exponential_smoothing_engine import (
    forecast_exponential_smoothing,
)


def _monthly_df(values):
    dates = pd.date_range("2024-01-01", periods=len(values), freq="MS")
    return pd.DataFrame({"date": dates, "quantity": values})


def test_konstan_menghasilkan_konstan():
    df = _monthly_df([50.0] * 20)
    res = forecast_exponential_smoothing(df, horizon=2)
    assert len(res.forecast) == 2
    for pt in res.forecast:
        assert pt.value == pytest.approx(50.0, abs=1e-6)
    assert res.mape == pytest.approx(0.0, abs=1e-6)


def test_metrik_lengkap():
    df = _monthly_df([10, 12, 11, 13, 15, 14, 16, 18, 17, 19, 21, 20, 22, 24, 23, 25])
    res = forecast_exponential_smoothing(df, horizon=3)
    for m in (res.mad, res.mfe, res.mse, res.mape):
        assert not math.isnan(m)
    assert res.mase is not None
