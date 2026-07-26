"""
TDD evaluation.py — metrik akurasi v3.0 (MAD/MFE/MSE/MAPE + MASE opsional).
Angka diverifikasi manual (AGENTS.md §3).
"""
import math

import numpy as np
import pytest

from app.services.forecasting import evaluation


def test_mad_rata_rata_absolute_error():
    actual = np.array([10.0, 20.0, 30.0])
    forecast = np.array([12.0, 18.0, 33.0])
    # |−2|+|2|+|−3| = 7 / 3
    assert evaluation.mad(actual, forecast) == pytest.approx(7 / 3)


def test_mfe_bias_bertanda():
    actual = np.array([10.0, 20.0, 30.0])
    forecast = np.array([12.0, 18.0, 33.0])
    # (10-12)+(20-18)+(30-33) = -3 / 3 = -1.0 (over-forecast → negatif)
    assert evaluation.mfe(actual, forecast) == pytest.approx(-1.0)


def test_mse_rata_rata_kuadrat_error():
    actual = np.array([10.0, 20.0, 30.0])
    forecast = np.array([12.0, 18.0, 33.0])
    # (4+4+9)/3
    assert evaluation.mse(actual, forecast) == pytest.approx(17 / 3)


def test_mape_persen_dan_guard_zero():
    actual = np.array([0.0, 100.0, 50.0])
    forecast = np.array([5.0, 90.0, 55.0])
    # periode actual=0 dikecualikan; sisa: |10/100| + |−5/50| = 0.1+0.1 = 0.2/2 = 0.1 → 10%
    assert evaluation.mape(actual, forecast) == pytest.approx(10.0)


def test_mape_semua_actual_nol_kembalikan_inf():
    actual = np.array([0.0, 0.0])
    forecast = np.array([3.0, 4.0])
    assert math.isinf(evaluation.mape(actual, forecast))


def test_backtest_metrics_lengkap_dengan_mase():
    actual = np.array([10.0, 20.0, 30.0])
    forecast = np.array([12.0, 18.0, 33.0])
    train = np.array([5.0, 7.0, 9.0, 11.0])
    m = evaluation.backtest_metrics(actual, forecast, train, compute_mase=True)
    assert set(m) == {"mad", "mfe", "mse", "mape", "mase"}
    assert m["mad"] == pytest.approx(7 / 3)
    assert m["mase"] is not None


def test_backtest_metrics_mase_none_saat_disabled():
    actual = np.array([10.0, 20.0])
    forecast = np.array([11.0, 19.0])
    m = evaluation.backtest_metrics(actual, forecast, np.array([1.0, 2.0]), compute_mase=False)
    assert m["mase"] is None
