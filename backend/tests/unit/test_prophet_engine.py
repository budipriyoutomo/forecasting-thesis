"""
Prophet belum diimplementasikan (lihat docstring modul) — test ini memastikan
pemanggilannya gagal jelas (NotImplementedError), bukan diam-diam silent-pass,
dan bahwa ia memang belum terdaftar di registry (AGENTS.md §5/#15, §6.6).
"""
import pytest

from app.services.forecasting.engines.prophet_engine import forecast_prophet
from app.services.forecasting.registry import MODEL_REGISTRY


def test_forecast_prophet_raises_not_implemented(smooth_df):
    with pytest.raises(NotImplementedError):
        forecast_prophet(smooth_df, horizon=7)


def test_prophet_not_yet_registered():
    assert "prophet" not in MODEL_REGISTRY
