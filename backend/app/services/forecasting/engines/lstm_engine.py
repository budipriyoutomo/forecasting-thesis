"""
LSTM — 1 fungsi (v3.0). Min-Max scaling, sequence window 12, 2× LSTM(50) + Dense(1),
optimizer Adam, loss MSE (Bab III thesis). Forecast rekursif multi-step.

TensorFlow di-import LAZY di dalam fungsi: bila TF tidak terpasang (mis. belum ada
wheel untuk versi Python berjalan), import modul registry TIDAK ikut gagal — fungsi
ini yang melempar error saat dipanggil, sehingga di mode otomatis engine ini otomatis
dikecualikan (AGENTS.md §5 failure per-engine) dan di mode manual errornya jelas.

Kontrak: docs/ARCHITECTURE.md §6.4 dan engines/README.md.
"""
import numpy as np

from app.config import get_settings
from app.services.forecasting.engines._common import build_points, resid_std
from app.services.forecasting.evaluation import backtest_metrics
from app.services.forecasting.metrics import train_test_split_series
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.types import EngineResult

_WINDOW = 12
_LSTM_UNITS = 50
_EPOCHS = 100
_BATCH = 32


def _build_sequences(scaled: np.ndarray, window: int):
    X, y = [], []
    for i in range(window, len(scaled)):
        X.append(scaled[i - window : i])
        y.append(scaled[i])
    X = np.asarray(X, dtype=float).reshape(-1, window, 1)
    return X, np.asarray(y, dtype=float)


def _lstm_forecast(values: np.ndarray, steps: int, window: int) -> np.ndarray:
    import tensorflow as tf  # lazy — lihat docstring modul

    tf.keras.utils.set_random_seed(42)

    values = np.asarray(values, dtype=float)
    window = min(window, max(2, len(values) // 2))
    vmin, vmax = float(values.min()), float(values.max())
    scale = (vmax - vmin) or 1.0
    scaled = (values - vmin) / scale

    X, y = _build_sequences(scaled, window)
    if len(X) == 0:
        raise ValueError("Data tidak cukup untuk membentuk sequence LSTM.")

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(window, 1)),
            tf.keras.layers.LSTM(_LSTM_UNITS, return_sequences=True),
            tf.keras.layers.LSTM(_LSTM_UNITS),
            tf.keras.layers.Dense(1),
        ]
    )
    model.compile(optimizer="adam", loss="mse")
    model.fit(X, y, epochs=_EPOCHS, batch_size=_BATCH, verbose=0)

    history = list(scaled)
    preds = []
    for _ in range(steps):
        seq = np.asarray(history[-window:], dtype=float).reshape(1, window, 1)
        p = float(model.predict(seq, verbose=0)[0][0])
        preds.append(p)
        history.append(p)

    return np.asarray(preds, dtype=float) * scale + vmin


def forecast_lstm(df, horizon: int) -> EngineResult:
    settings = get_settings()
    series = to_period_series(df)
    _, test = train_test_split_series(series, horizon)
    train = series.iloc[: len(series) - len(test)]

    test_pred = _lstm_forecast(train.to_numpy(), len(test), _WINDOW)
    metrics = backtest_metrics(
        test.to_numpy(), test_pred, train.to_numpy(), compute_mase=settings.COMPUTE_MASE
    )

    values = _lstm_forecast(series.to_numpy(), horizon, _WINDOW)
    std = resid_std(test.to_numpy(), test_pred, series)
    points = build_points(series, values, std)
    explanation = (
        f"LSTM (2 lapis {_LSTM_UNITS} unit, window {_WINDOW}) mempelajari dependensi "
        f"temporal jangka panjang. MAPE backtest: {metrics['mape']:.2f}%."
    )
    return EngineResult(forecast=points, explanation=explanation, **metrics)
