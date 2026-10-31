"""
Utilitas supervised-learning bersama untuk engine ML (Random Forest, XGBoost) —
BUKAN metode forecasting (diawali `_`, tak didaftarkan), jadi tidak melanggar
1-fungsi-1-metode (AGENTS.md §5).

Membentuk fitur lag + kalender (+ variabel eksternal aktif, Fase 11.2b) dari time
series & melakukan forecast rekursif multi-step. Set lag disesuaikan panjang data
(data thesis bulanan; lag yang melebihi panjang histori otomatis dibuang).

Fase 11.2 (REVISI_V2 §3.6): feature importance (embedded RF/XGB), grid search
`GridSearchCV` + `TimeSeriesSplit` (opsional), dan cap outlier IQR (opsional).
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

from app.services.forecasting.metrics import train_test_split_series
from app.services.forecasting.preprocessing import cap_outliers_iqr, future_timestamps, infer_period_delta
from app.services.forecasting.types import EngineOptions

# Grid search hanya dijalankan bila sampel supervised train cukup untuk ≥ 2 fold.
MIN_TUNING_SAMPLES = 6


def usable_lags(n: int, lags: list[int]) -> list[int]:
    fit = [lag for lag in lags if lag < n]
    return fit or ([1] if n > 1 else [])


def future_index(series: pd.Series, horizon: int) -> list[pd.Timestamp]:
    return future_timestamps(series.index.max(), horizon, infer_period_delta(series.index))


def usable_exog(exog: pd.DataFrame | None, periods) -> tuple[pd.DataFrame | None, list[str]]:
    """Kolom variabel eksternal yang nilainya lengkap untuk SELURUH `periods`
    (histori + horizon). Return (exog terpakai | None, kode yang di-drop)."""
    if exog is None or exog.empty:
        return None, []
    idx = pd.DatetimeIndex(pd.to_datetime(list(periods)))
    aligned = exog.copy()
    aligned.index = pd.DatetimeIndex(pd.to_datetime(aligned.index))
    aligned = aligned.reindex(idx)
    keep = [c for c in aligned.columns if aligned[c].notna().all()]
    dropped = [str(c) for c in aligned.columns if c not in keep]
    return (aligned[keep] if keep else None), dropped


def _row(values, i_or_step, lags, month, exog_row) -> list[float]:
    return [values[i_or_step - lag] for lag in lags] + [int(month)] + list(exog_row)


def build_supervised(
    series: pd.Series, lags: list[int], exog: pd.DataFrame | None = None
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Bangun matriks fitur [lag..., bulan, exog...] → target. Baris < max(lag) dibuang."""
    values = series.to_numpy(dtype=float)
    months = series.index.month
    n = len(values)
    lags = usable_lags(n, lags)
    start = max(lags) if lags else 1
    ex = exog.reindex(series.index).to_numpy(dtype=float) if exog is not None else np.zeros((n, 0))
    rows, targets = [], []
    for i in range(start, n):
        rows.append(_row(values, i, lags, months[i], ex[i]))
        targets.append(values[i])
    return np.asarray(rows, dtype=float), np.asarray(targets, dtype=float), lags


def recursive_forecast(
    model, series: pd.Series, lags: list[int], horizon: int, exog: pd.DataFrame | None = None
) -> np.ndarray:
    """Prediksi horizon ke depan secara rekursif (prediksi jadi input lag berikutnya)."""
    values = list(series.to_numpy(dtype=float))
    steps = future_index(series, horizon)
    preds = []
    for step in steps:
        exog_row = exog.loc[step].to_numpy(dtype=float) if exog is not None else []
        row = [values[-lag] for lag in lags] + [int(step.month)] + list(exog_row)
        pred = float(model.predict(np.asarray([row], dtype=float))[0])
        preds.append(pred)
        values.append(pred)
    return np.asarray(preds, dtype=float)


def feature_names(lags: list[int], exog: pd.DataFrame | None) -> list[str]:
    return [f"lag_{lag}" for lag in lags] + ["month"] + ([str(c) for c in exog.columns] if exog is not None else [])


def importance_dict(model, names: list[str]) -> dict[str, float]:
    """`feature_importances_` ternormalisasi (Σ = 1), terurut menurun."""
    raw = np.asarray(getattr(model, "feature_importances_", np.zeros(len(names))), dtype=float)
    total = raw.sum()
    weights = raw / total if total > 0 else np.full(len(names), 1 / max(len(names), 1))
    pairs = sorted(zip(names, weights), key=lambda p: p[1], reverse=True)
    return {name: float(w) for name, w in pairs}


def tune(model_factory, param_grid: dict, X: np.ndarray, y: np.ndarray) -> tuple[dict | None, int]:
    """GridSearchCV + TimeSeriesSplit (skor MAD). Sampel kurang → (None, 0)."""
    if len(X) < MIN_TUNING_SAMPLES:
        return None, 0
    n_splits = min(3, len(X) // 2)
    search = GridSearchCV(
        model_factory(), param_grid, cv=TimeSeriesSplit(n_splits=n_splits), scoring="neg_mean_absolute_error"
    )
    search.fit(X, y)
    return dict(search.best_params_), n_splits


@dataclass
class SupervisedRun:
    train: pd.Series
    test: pd.Series
    test_pred: np.ndarray
    values: np.ndarray
    lags: list[int]
    feature_importance: dict[str, float]
    hyperparameters: dict


def run_supervised(
    model_factory, param_grid: dict, df_series: pd.Series, lags: list[int], horizon: int,
    options: EngineOptions | None = None,
) -> SupervisedRun:
    """Backtest holdout + fit ulang seluruh data + forecast rekursif.

    Grid search (bila aktif) di-tuning pada data TRAIN saja (tanpa bocor ke holdout);
    parameter terbaik dipakai untuk backtest & model final. Outlier di-cap di data
    training saja — metrik tetap dihitung terhadap aktual asli.
    """
    options = options or EngineOptions()
    series = df_series
    _, test = train_test_split_series(series, horizon)
    train = series.iloc[: len(series) - len(test)]

    exog, dropped = usable_exog(options.exog, list(series.index) + future_index(series, horizon))

    n_capped = 0
    train_fit, full_fit = train, series
    if options.ml_winsorize:
        train_fit, _ = cap_outliers_iqr(train)
        full_fit, n_capped = cap_outliers_iqr(series)

    X_tr, y_tr, used_tr = build_supervised(train_fit, lags, exog)
    if len(X_tr) == 0:
        raise ValueError("Data tidak cukup untuk membentuk fitur supervised.")

    best_params, n_splits = (None, 0)
    if options.ml_grid_search:
        best_params, n_splits = tune(model_factory, param_grid, X_tr, y_tr)

    def make():
        model = model_factory()
        if best_params:
            model.set_params(**best_params)
        return model

    bt_model = make()
    bt_model.fit(X_tr, y_tr)
    test_pred = recursive_forecast(bt_model, train_fit, used_tr, len(test), exog)

    X, y, used = build_supervised(full_fit, lags, exog)
    model = make()
    model.fit(X, y)
    values = recursive_forecast(model, full_fit, used, horizon, exog)

    hyperparameters = {
        "grid_search": best_params is not None,
        "cv_splits": n_splits,
        "best_params": best_params or {k: v for k, v in model.get_params().items() if k in param_grid},
        "outliers_capped": n_capped,
        "exog_used": [str(c) for c in exog.columns] if exog is not None else [],
        "exog_dropped": dropped,
    }
    return SupervisedRun(
        train=train,
        test=test,
        test_pred=test_pred,
        values=values,
        lags=used,
        feature_importance=importance_dict(model, feature_names(used, exog)),
        hyperparameters=hyperparameters,
    )
