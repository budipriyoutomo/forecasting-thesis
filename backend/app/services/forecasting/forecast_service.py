"""
Orkestrasi Forecasting v3.0 — Comparative Selection + Manual Override.

SATU-SATUNYA entry point engine — endpoint TIDAK BOLEH memanggil registry/engine
langsung (AGENTS.md §5).

Alur (docs/ARCHITECTURE.md §6.1):
  - `requested_method` diisi → MODE MANUAL: langsung panggil 1 fungsi metode itu.
    Gagal → error langsung, TIDAK fallback (user memilih sadar — AGENTS.md §5/#14).
  - `requested_method` None  → MODE OTOMATIS: jalankan SELURUH metode aktif,
    hitung MAD/MFE/MSE/MAPE tiap metode, pilih metrik ranking terbaik
    (`ranking_metric`, dari master data Pengaturan Forecast — bukan env).
    Tak ada klasifikasi kuadran (larangan #12).

Fase 11.2a (Keputusan #6): tiap kandidat mode otomatis membawa 3 peringkat
berdampingan — `rank_mad`, `rank_mfe` (|MFE|), `rank_mape` — sebagai acuan planner.
"""
import logging
import math
from dataclasses import dataclass

import pandas as pd

from app.config import get_settings
from app.services.forecasting import registry
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.evaluation import mape_interpretation
from app.services.forecasting.types import EngineOptions, EngineResult, ForecastPoint
from app.utils.exceptions import UnsupportedForecastMethodError

log = logging.getLogger(__name__)

_VALID_RANKING = {"mape", "mad", "mse", "mfe_abs"}
DEFAULT_RANKING_METRIC = "mad"  # dipakai bila master data belum diisi (Keputusan #6)

# kolom peringkat → (kunci metrik di kandidat, pakai nilai mutlak?)
_RANK_COLUMNS = {"rank_mad": ("mad", False), "rank_mfe": ("mfe", True), "rank_mape": ("mape", False)}


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
    feature_importance: dict | None = None  # Fase 11.2 — RF/XGB pemenang
    hyperparameters: dict | None = None  # α ES / hasil grid search / outlier di-cap


def _ranking_value(result: EngineResult, metric: str) -> float:
    metric = metric if metric in _VALID_RANKING else DEFAULT_RANKING_METRIC
    value = abs(result.mfe) if metric == "mfe_abs" else getattr(result, metric)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("inf")  # metode dgn metrik tak terdefinisi dianggap terburuk
    return float(value)


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
    }


def _fmt_metric(value: float | None, metric: str) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "tak terdefinisi"
    return f"{value:.2f}%" if metric == "mape" else f"{value:.2f}"


def _comparison_note(winner: str, metric: str, candidates: list[dict]) -> str:
    """Narasi kenapa pemenang menang — dasar perbandingan yang tersimpan di
    `candidates_evaluated`, ditulis untuk planner non-teknis (PRD FR-3.4/3.5).

    Hanya untuk mode otomatis: mode manual tidak membandingkan apa pun.
    """
    key = "mfe" if metric == "mfe_abs" else metric
    label = "MFE (nilai mutlak)" if metric == "mfe_abs" else metric.upper()
    ranked = sorted(candidates, key=lambda c: _ranking_key(c, metric))

    winner_row = next((c for c in ranked if c["method"] == winner), None)
    winner_value = _fmt_metric(winner_row.get(key) if winner_row else None, key)
    note = (
        f"Dipilih otomatis: {winner} menang atas {len(candidates)} metode yang "
        f"dibandingkan, dengan {label} terendah ({winner_value})."
    )

    runner_up = next((c for c in ranked if c["method"] != winner), None)
    if runner_up is not None:
        note += (
            f" Terbaik berikutnya {runner_up['method']} "
            f"({_fmt_metric(runner_up.get(key), key)})."
        )
    return note


def _ranking_key(candidate: dict, metric: str) -> float:
    key = "mfe" if metric == "mfe_abs" else (metric if metric in _VALID_RANKING else DEFAULT_RANKING_METRIC)
    value = candidate.get(key)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("inf")
    return abs(float(value)) if metric == "mfe_abs" else float(value)


def _defined(value) -> bool:
    return value is not None and math.isfinite(float(value))


def rank_candidates(candidates: list[dict]) -> list[dict]:
    """Salinan `candidates` + `rank_mad`/`rank_mfe`/`rank_mape` (1 = terbaik).

    Seri → peringkat sama lalu dilompati (1, 1, 3); metrik tak terdefinisi → None.
    """
    ranked = [dict(c) for c in candidates]
    for column, (key, absolute) in _RANK_COLUMNS.items():
        values = [
            (abs(float(c[key])) if absolute else float(c[key])) if _defined(c.get(key)) else None
            for c in ranked
        ]
        defined = [v for v in values if v is not None]
        for c, v in zip(ranked, values):
            c[column] = None if v is None else 1 + sum(1 for other in defined if other < v)
    return ranked


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
    ranking_metric: str = DEFAULT_RANKING_METRIC,
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

    metric = ranking_metric if ranking_metric in _VALID_RANKING else DEFAULT_RANKING_METRIC
    method_name, result = min(evaluated, key=lambda item: _ranking_value(item[1], metric))
    candidates = rank_candidates([_candidate_row(name, r) for name, r in evaluated])
    record = _completed(method_name, "auto", result, candidates)
    # Narasi perbandingan di depan penjelasan engine — planner perlu tahu dasar
    # pemilihannya lebih dulu, baru karakteristik metodenya.
    note = _comparison_note(method_name, metric, candidates)
    record.explanation = f"{note} {record.explanation}".strip() if record.explanation else note
    return record
