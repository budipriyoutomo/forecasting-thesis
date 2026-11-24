"""
TDD lstm engine v3.0. TensorFlow di-skip bila tak terpasang (mis. Python 3.14
belum ada wheel TF) — engine tetap ada di registry & auto-excluded saat dipanggil.
"""
import math

import pandas as pd
import pytest

pytest.importorskip("tensorflow")

from app.services.forecasting.engines import lstm_engine  # noqa: E402
from app.services.forecasting.engines.lstm_engine import forecast_lstm  # noqa: E402


@pytest.fixture(autouse=True)
def _timeout_longgar(monkeypatch):
    """Training asli 100 epoch di child process; batas 120 dtk production bisa terlampaui di
    mesin dev/CI yang sibuk → longgarkan supaya test ini menguji model, bukan beban mesin.
    Perilaku timeout sendiri diuji di test_engine_isolation.py."""
    from app.config import get_settings

    relaxed = get_settings().model_copy(update={"LSTM_ENGINE_TIMEOUT_SECONDS": 900})
    monkeypatch.setattr(lstm_engine, "get_settings", lambda: relaxed)


def _monthly_df(values):
    dates = pd.date_range("2021-01-01", periods=len(values), freq="MS")
    return pd.DataFrame({"date": dates, "quantity": values})


def test_menghasilkan_horizon_dan_metrik():
    values = [100 + i * 2 for i in range(40)]
    res = forecast_lstm(_monthly_df(values), horizon=3)
    assert len(res.forecast) == 3
    for pt in res.forecast:
        assert math.isfinite(pt.value)
    for m in (res.mad, res.mfe, res.mse, res.mape):
        assert math.isfinite(m)
