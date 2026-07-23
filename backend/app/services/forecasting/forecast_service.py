"""
Orkestrasi Auto Model Selection Engine + Manual Override.

SATU-SATUNYA entry point untuk menjalankan forecast — endpoint TIDAK BOLEH
memanggil classification/registry/scoring_engine langsung (AGENTS.md §5).

Alur:
  - `requested_method` diisi  → MODE MANUAL: skip klasifikasi+scoring,
    langsung panggil 1 fungsi metode itu. Gagal → error langsung, TIDAK
    fallback ke metode lain (user sudah memilih sadar — lihat AGENTS.md §5/#14).
  - `requested_method` None   → MODE OTOMATIS: klasifikasi → filter kandidat
    per kuadran → backtest tiap kandidat → weighted scoring → skor tertinggi menang.
"""
from dataclasses import dataclass

import pandas as pd

from app.config import get_settings
from app.services.forecasting import classification, registry, scoring_engine
from app.services.forecasting.preprocessing import to_daily_series
from app.services.forecasting.types import ForecastPoint
from app.utils.exceptions import UnsupportedForecastMethodError


@dataclass
class ForecastResultRecord:
    status: str  # "COMPLETED" | "INSUFFICIENT_DATA" | "MODEL_SELECTION_FAILED"
    method_used: str | None = None
    selection_mode: str | None = None  # "auto" | "manual"
    demand_class: str | None = None
    forecast: list[ForecastPoint] | None = None
    mase: float | None = None
    explanation: str | None = None


def run_forecast_for_material(
    df: pd.DataFrame, horizon: int, requested_method: str | None = None
) -> ForecastResultRecord:
    settings = get_settings()

    # Gate pakai panjang rentang kalender (bukan jumlah baris mentah) — item
    # intermittent/lumpy secara alami punya sedikit baris observasi meski
    # rentang historisnya panjang, jadi tidak boleh salah dianggap kurang data.
    daily_series_length = len(to_daily_series(df))
    if daily_series_length < settings.BACKTEST_MIN_PERIODS:
        return ForecastResultRecord(status="INSUFFICIENT_DATA")

    profile = classification.classify(df)

    # ── MODE MANUAL ──────────────────────────────────────────────────────
    if requested_method is not None:
        enabled = registry.get_enabled_methods()
        if requested_method not in enabled:
            raise UnsupportedForecastMethodError(
                f"Metode '{requested_method}' tidak dikenal atau tidak aktif"
            )

        forecast_fn = registry.MODEL_REGISTRY[requested_method]
        try:
            result = forecast_fn(df, horizon)
        except Exception:
            # TIDAK fallback ke metode lain di mode manual (AGENTS.md §5/#14)
            return ForecastResultRecord(
                status="MODEL_SELECTION_FAILED",
                method_used=requested_method,
                selection_mode="manual",
                demand_class=profile.demand_class,
            )

        return ForecastResultRecord(
            status="COMPLETED",
            method_used=requested_method,
            selection_mode="manual",
            demand_class=profile.demand_class,
            forecast=result.forecast,
            mase=result.mase,
            explanation=result.explanation,
        )

    # ── MODE OTOMATIS ────────────────────────────────────────────────────
    candidates = registry.filter_candidates(profile)
    if not candidates:
        return ForecastResultRecord(status="MODEL_SELECTION_FAILED", demand_class=profile.demand_class)

    scored = []
    for method_name in candidates:
        forecast_fn = registry.MODEL_REGISTRY[method_name]
        try:
            result = forecast_fn(df, horizon)
            penalty = scoring_engine.guardrail_penalty(df, result)
            score = scoring_engine.compute_score(result.mase, penalty, profile, method_name)
            scored.append((method_name, score, result))
        except Exception:
            continue  # exclude kandidat yang gagal, lanjut ke kandidat lain

    if not scored:
        return ForecastResultRecord(status="MODEL_SELECTION_FAILED", demand_class=profile.demand_class)

    scored.sort(key=lambda item: item[1], reverse=True)
    method_name, _, result = scored[0]

    return ForecastResultRecord(
        status="COMPLETED",
        method_used=method_name,
        selection_mode="auto",
        demand_class=profile.demand_class,
        forecast=result.forecast,
        mase=result.mase,
        explanation=result.explanation,
    )
