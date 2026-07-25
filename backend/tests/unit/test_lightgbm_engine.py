"""Test forecast_lightgbm — 1 fungsi, 1 metode (AGENTS.md §5)."""
import math

from app.services.forecasting.engines.legacy.lightgbm_engine import forecast_lightgbm


def test_forecast_lightgbm_happy_path(erratic_df):
    result = forecast_lightgbm(erratic_df, horizon=7)

    assert len(result.forecast) == 7
    assert math.isfinite(result.mase)
    assert "LightGBM" in result.explanation
    for point in result.forecast:
        assert point.lower <= point.upper
