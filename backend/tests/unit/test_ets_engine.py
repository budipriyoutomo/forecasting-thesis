"""Test forecast_ets — 1 fungsi, 1 metode (AGENTS.md §5)."""
import math

from app.services.forecasting.engines.legacy.ets_engine import forecast_ets


def test_forecast_ets_happy_path(smooth_df):
    result = forecast_ets(smooth_df, horizon=7)

    assert len(result.forecast) == 7
    assert math.isfinite(result.mase)
    assert result.mase >= 0
    assert "ETS" in result.explanation
    for point in result.forecast:
        assert point.lower <= point.value <= point.upper


def test_forecast_ets_returns_reasonable_values_for_stable_series(smooth_df):
    result = forecast_ets(smooth_df, horizon=5)
    # Data historis berkisar 20-22, forecast seharusnya di rentang yang masuk akal
    for point in result.forecast:
        assert 0 <= point.value <= 100
