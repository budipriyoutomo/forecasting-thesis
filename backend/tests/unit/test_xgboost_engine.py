"""TDD xgboost engine v3.0 — fitur lag + kalender, forecast rekursif."""
import math

import numpy as np
import pandas as pd

from app.services.forecasting.engines.xgboost_engine import forecast_xgboost


def _monthly_df(values):
    dates = pd.date_range("2021-01-01", periods=len(values), freq="MS")
    return pd.DataFrame({"date": dates, "quantity": values})


def test_menghasilkan_horizon_dan_metrik_finite():
    rng = np.random.default_rng(1)
    base = 200 + np.arange(36) * 1.5 + rng.normal(0, 4, 36)
    res = forecast_xgboost(_monthly_df(base), horizon=3)
    assert len(res.forecast) == 3
    for pt in res.forecast:
        assert math.isfinite(pt.value)
        assert pt.lower <= pt.value <= pt.upper
    for m in (res.mad, res.mfe, res.mse, res.mape):
        assert math.isfinite(m)
    assert res.mase is not None


def test_deterministik():
    df = _monthly_df([10, 12, 14, 13, 15, 17, 16, 18, 20, 19, 21, 23,
                      22, 24, 26, 25, 27, 29, 28, 30, 32, 31, 33, 35])
    a = forecast_xgboost(df, horizon=2)
    b = forecast_xgboost(df, horizon=2)
    assert [p.value for p in a.forecast] == [p.value for p in b.forecast]
