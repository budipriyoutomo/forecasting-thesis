"""
Test orkestrasi forecast_service — mode otomatis vs manual (AGENTS.md §5,
docs/ARCHITECTURE.md §6.1).
"""
import pytest

from app.services.forecasting.forecast_service import run_forecast_for_material
from app.utils.exceptions import UnsupportedForecastMethodError


def test_auto_mode_selects_croston_for_lumpy_pattern(lumpy_df):
    record = run_forecast_for_material(lumpy_df, horizon=10, requested_method=None)

    assert record.status == "COMPLETED"
    assert record.selection_mode == "auto"
    assert record.method_used == "croston"  # satu-satunya kandidat untuk kuadran lumpy
    assert record.demand_class == "lumpy"
    assert len(record.forecast) == 10


def test_auto_mode_selects_candidate_for_smooth_pattern(smooth_df):
    record = run_forecast_for_material(smooth_df, horizon=7, requested_method=None)

    assert record.status == "COMPLETED"
    assert record.selection_mode == "auto"
    assert record.method_used in {"ets", "arima"}  # kandidat kuadran smooth


def test_manual_mode_forces_requested_method(smooth_df):
    record = run_forecast_for_material(smooth_df, horizon=7, requested_method="arima")

    assert record.status == "COMPLETED"
    assert record.selection_mode == "manual"
    assert record.method_used == "arima"


def test_manual_mode_allows_method_outside_quadrant_mapping(lumpy_df):
    # Planner secara sadar minta ARIMA meski datanya lumpy — sistem HARUS
    # mengizinkan (§6.3: mode manual tidak dibatasi peta kuadran).
    record = run_forecast_for_material(lumpy_df, horizon=5, requested_method="arima")

    assert record.selection_mode == "manual"
    assert record.method_used == "arima"


def test_manual_mode_unknown_method_raises_error(smooth_df):
    with pytest.raises(UnsupportedForecastMethodError):
        run_forecast_for_material(smooth_df, horizon=7, requested_method="prophet")


def test_insufficient_data_returns_status(too_short_df):
    record = run_forecast_for_material(too_short_df, horizon=7, requested_method=None)

    assert record.status == "INSUFFICIENT_DATA"
