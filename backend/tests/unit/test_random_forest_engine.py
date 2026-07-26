"""TDD random_forest engine v3.0 — fitur lag + kalender, forecast rekursif."""
import math

import numpy as np
import pandas as pd

from app.services.forecasting.engines.random_forest_engine import forecast_random_forest


def _monthly_df(values):
    dates = pd.date_range("2022-01-01", periods=len(values), freq="MS")
    return pd.DataFrame({"date": dates, "quantity": values})


def test_menghasilkan_horizon_dan_metrik_finite():
    rng = np.random.default_rng(0)
    base = 100 + np.arange(36) * 2 + rng.normal(0, 3, 36)
    res = forecast_random_forest(_monthly_df(base), horizon=3)
    assert len(res.forecast) == 3
    for pt in res.forecast:
        assert math.isfinite(pt.value)
        assert pt.lower <= pt.value <= pt.upper
    for m in (res.mad, res.mfe, res.mse, res.mape):
        assert math.isfinite(m)
    assert res.mase is not None


def test_deterministik_dgn_random_state():
    df = _monthly_df([10, 12, 14, 13, 15, 17, 16, 18, 20, 19, 21, 23,
                      22, 24, 26, 25, 27, 29, 28, 30, 32, 31, 33, 35])
    a = forecast_random_forest(df, horizon=2)
    b = forecast_random_forest(df, horizon=2)
    assert [p.value for p in a.forecast] == [p.value for p in b.forecast]
