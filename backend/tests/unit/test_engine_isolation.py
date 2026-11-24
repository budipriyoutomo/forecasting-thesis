"""
Isolasi proses untuk engine berat (24 Nov 2026) — LSTM/TensorFlow dijalankan di child process.

Laporan user: generate forecast di VPS → "Permintaan gagal (status 502)". TensorFlow yang crash
(OOM-kill kernel / SIGILL karena CPU tanpa AVX) membunuh SELURUH worker uvicorn — `except
Exception` di `_evaluate_all` tidak bisa menangkapnya. Dengan child process, crash/timeout jadi
exception biasa → metode tercatat gagal + alasan, run tetap selesai (AGENTS #8).
"""
import importlib.util
import os
import signal
import time

import numpy as np
import pytest

from app.services.forecasting.engines._isolation import EngineCrashError, run_isolated
from app.services.forecasting.forecast_service import _failure_reason


# Fungsi target wajib level modul (di-pickle ke child process `spawn`).
def _double(values):
    return np.asarray(values) * 2


def _raise_value_error():
    raise ValueError("Data tidak cukup untuk membentuk sequence LSTM.")


def _raise_tf_missing():
    raise ModuleNotFoundError("No module named 'tensorflow'", name="tensorflow")


def _kill_self(sig):
    os.kill(os.getpid(), sig)
    time.sleep(5)


def _sleep(seconds):
    time.sleep(seconds)


def test_hasil_child_dikembalikan():
    out = run_isolated(_double, ([1.0, 2.0],), timeout=60)
    assert out.tolist() == [2.0, 4.0]


def test_exception_child_diteruskan_dengan_tipe_sama():
    with pytest.raises(ValueError, match="sequence LSTM"):
        run_isolated(_raise_value_error, (), timeout=60)


def test_tensorflow_absen_tetap_terbaca_sebagai_tensorflow():
    with pytest.raises(ModuleNotFoundError) as info:
        run_isolated(_raise_tf_missing, (), timeout=60)
    assert info.value.name == "tensorflow"
    assert "TensorFlow belum terpasang" in _failure_reason(info.value)


def test_child_dibunuh_sigkill_jadi_error_kehabisan_memori():
    with pytest.raises(EngineCrashError) as info:
        run_isolated(_kill_self, (signal.SIGKILL,), timeout=60)
    assert "memori" in str(info.value)
    assert str(info.value) in _failure_reason(info.value)


def test_child_sigill_menyebut_avx():
    with pytest.raises(EngineCrashError, match="AVX"):
        run_isolated(_kill_self, (signal.SIGILL,), timeout=60)


def test_timeout_menghentikan_child():
    start = time.monotonic()
    with pytest.raises(EngineCrashError, match="batas waktu"):
        run_isolated(_sleep, (30,), timeout=1)
    assert time.monotonic() - start < 15


@pytest.mark.skipif(importlib.util.find_spec("tensorflow") is not None, reason="TF terpasang")
def test_forecast_lstm_tanpa_tf_raise_modulenotfound_tensorflow():
    import pandas as pd

    from app.services.forecasting.engines.lstm_engine import forecast_lstm

    df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=24, freq="MS"), "quantity": range(24)})
    with pytest.raises(ModuleNotFoundError) as info:
        forecast_lstm(df, 3)
    assert info.value.name == "tensorflow"
