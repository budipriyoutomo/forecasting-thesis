"""Test forecast_croston — 1 fungsi, 1 metode, wajib untuk intermittent/lumpy (AGENTS.md §5)."""
import math

from app.services.forecasting.engines.legacy.croston_engine import forecast_croston


def test_forecast_croston_on_intermittent_pattern(intermittent_df):
    result = forecast_croston(intermittent_df, horizon=10)

    assert len(result.forecast) == 10
    assert math.isfinite(result.mase)
    assert "Croston" in result.explanation
    # Rate hasil Croston harus konstan sepanjang horizon (ciri khas metode ini)
    values = {round(p.value, 6) for p in result.forecast}
    assert len(values) == 1


def test_forecast_croston_on_lumpy_pattern(lumpy_df):
    result = forecast_croston(lumpy_df, horizon=10)

    assert len(result.forecast) == 10
    assert result.forecast[0].value > 0  # ada demand rate yang terdeteksi, bukan 0 semua


def test_forecast_croston_handles_no_demand_at_all():
    import pandas as pd

    df = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=20).astype(str), "quantity": [0] * 20})
    result = forecast_croston(df, horizon=5)

    assert len(result.forecast) == 5
    assert all(p.value == 0 for p in result.forecast)
