"""
Orkestrasi Forecasting — mode otomatis (semua metode, tanpa pemenang) + mode manual.

SATU-SATUNYA entry point engine — endpoint TIDAK BOLEH memanggil registry/engine
langsung (AGENTS.md §5).

Alur (docs/ARCHITECTURE.md §6.1):
  - `requested_method` diisi → MODE MANUAL: langsung panggil 1 fungsi metode itu.
    Gagal → error langsung, TIDAK fallback (user memilih sadar — AGENTS.md §5/#14).
    Metode itu langsung berlaku untuk produk ini.
  - `requested_method` None  → MODE OTOMATIS: jalankan SELURUH metode aktif, simpan
    MAD/MFE/MSE/MAPE + deret forecast + penjelasan tiap metode di `candidates_evaluated`.
    Sistem TIDAK memilih pemenang dan tidak memberi peringkat (Fase 11.15, keputusan user
    10 Nov 2026) — planner memilih metode per produk (override append-only, lihat
    `forecast_selection_service`). Tak ada klasifikasi kuadran (larangan #12).
"""
import logging
from dataclasses import dataclass

import pandas as pd

from app.config import get_settings
from app.services.forecasting import registry
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.evaluation import mape_interpretation
from app.services.forecasting.types import EngineOptions, EngineResult, ForecastPoint
from app.utils.exceptions import UnsupportedForecastMethodError

log = logging.getLogger(__name__)

@dataclass
class ForecastResultRecord:
    status: str  # "COMPLETED" | "INSUFFICIENT_DATA" | "MODEL_SELECTION_FAILED"
    method_used: str | None = None
    selection_mode: str | None = None  # "auto" | "manual"
    forecast: list[ForecastPoint] | None = None
    mad: float | None = None
    mfe: float | None = None
    mse: float | None = None
    mape: float | None = None
    mase: float | None = None
    candidates_evaluated: list[dict] | None = None
    explanation: str | None = None
    feature_importance: dict | None = None  # Fase 11.2 — RF/XGB (mode manual)
    hyperparameters: dict | None = None  # α ES / hasil grid search / outlier di-cap


def _candidate_row(method: str, r: EngineResult) -> dict:
    return {
        "method": method,
        "mad": r.mad,
        "mfe": r.mfe,
        "mse": r.mse,
        "mape": r.mape,
        "mase": r.mase,
        "feature_importance": r.feature_importance,
        "hyperparameters": r.hyperparameters,
        # Fase 11.15 — deret & penjelasan tiap kandidat disimpan agar planner bisa memilih
        # metode SETELAH run (mode otomatis tidak lagi memilih pemenang).
        "forecast": [p.__dict__ for p in r.forecast] if r.forecast else [],
        "explanation": _with_mape_label(r.explanation, r.mape),
    }


def _completed(method: str, mode: str, r: EngineResult, candidates: list[dict]) -> ForecastResultRecord:
    return ForecastResultRecord(
        status="COMPLETED",
        method_used=method,
        selection_mode=mode,
        forecast=r.forecast,
        mad=r.mad,
        mfe=r.mfe,
        mse=r.mse,
        mape=r.mape,
        mase=r.mase,
        candidates_evaluated=candidates,
        explanation=_with_mape_label(r.explanation, r.mape),
        feature_importance=r.feature_importance,
        hyperparameters=r.hyperparameters,
    )


def _with_mape_label(explanation: str | None, value) -> str:
    label = f"Interpretasi MAPE: {mape_interpretation(value)}."
    return f"{explanation} {label}".strip() if explanation else label


def run_forecast_for_product(
    df: pd.DataFrame,
    horizon: int,
    requested_method: str | None = None,
    enabled_methods: set[str] | None = None,
    options: EngineOptions | None = None,
) -> ForecastResultRecord:
    settings = get_settings()
    enabled = registry.get_enabled_methods(enabled_methods)

    if df.empty or "date" not in df.columns or df["quantity"].dropna().empty:
        return ForecastResultRecord(status="INSUFFICIENT_DATA")

    series = to_period_series(df)
    min_periods = settings.LSTM_MIN_PERIODS if requested_method == "lstm" else settings.BACKTEST_MIN_PERIODS
    if len(series) < min_periods:
        return ForecastResultRecord(status="INSUFFICIENT_DATA")

    # ── MODE MANUAL ──────────────────────────────────────────────────────
    if requested_method is not None:
        if requested_method not in enabled:
            raise UnsupportedForecastMethodError(
                f"Metode '{requested_method}' tidak dikenal atau tidak aktif"
            )
        forecast_fn = registry.MODEL_REGISTRY[requested_method]
        try:
            result = forecast_fn(df, horizon, options=options)
        except Exception:  # TIDAK fallback di mode manual (AGENTS.md §5/#14)
            log.warning("Metode manual '%s' gagal", requested_method, exc_info=True)
            return ForecastResultRecord(
                status="MODEL_SELECTION_FAILED", method_used=requested_method, selection_mode="manual"
            )
        return _completed(requested_method, "manual", result, [_candidate_row(requested_method, result)])

    # ── MODE OTOMATIS: Comparative Selection ─────────────────────────────
    evaluated: list[tuple[str, EngineResult]] = []
    for method_name in sorted(enabled):  # sorted → ranking stabil saat seri
        forecast_fn = registry.MODEL_REGISTRY[method_name]
        try:
            evaluated.append((method_name, forecast_fn(df, horizon, options=options)))
        except Exception:
            log.warning("Metode '%s' gagal saat backtest/fit, dikecualikan", method_name, exc_info=True)

    if not evaluated:
        return ForecastResultRecord(status="MODEL_SELECTION_FAILED")

    candidates = [_candidate_row(name, r) for name, r in evaluated]
    return ForecastResultRecord(
        status="COMPLETED",
        selection_mode="auto",
        candidates_evaluated=candidates,
        explanation=(
            f"{len(candidates)} metode dijalankan: {', '.join(c['method'] for c in candidates)}. "
            "Sistem tidak memilih metode otomatis — pilih metode yang dipakai untuk produk ini "
            "setelah membandingkan metrik dan grafik tiap metode."
        ),
    )
