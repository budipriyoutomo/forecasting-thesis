"""Test forecast_arima — 1 fungsi, 1 metode (AGENTS.md §5)."""
import math

from app.services.forecasting.engines.arima_engine import forecast_arima


def test_forecast_arima_happy_path(smooth_df):
    result = forecast_arima(smooth_df, horizon=7)

    assert len(result.forecast) == 7
    assert math.isfinite(result.mase)
    assert result.mase >= 0
    assert "ARIMA" in result.explanation
    for point in result.forecast:
        assert point.lower <= point.upper
