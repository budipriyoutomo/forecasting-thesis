"""
Orkestrasi Forecasting — mode otomatis (semua metode → terbaik dipilih) + mode manual.

SATU-SATUNYA entry point engine — endpoint TIDAK BOLEH memanggil registry/engine
langsung (AGENTS.md §5).

Alur (docs/ARCHITECTURE.md §6.1):
  - `requested_method` diisi → MODE MANUAL: langsung panggil 1 fungsi metode itu.
    Gagal → error langsung, TIDAK fallback (user memilih sadar — AGENTS.md §5/#14).
    Metode itu langsung berlaku untuk produk ini.
  - `requested_method` None  → MODE OTOMATIS: jalankan SELURUH metode aktif, simpan
    MAD/MFE/MSE/MAPE + deret forecast + penjelasan + peringkat tiap metode di
    `candidates_evaluated`, lalu sistem MEMILIH metode terbaik berdasarkan pengujian peramalan
    (`selection.select_best_method`, 23 Nov 2026 — membalik Fase 11.15 atas permintaan user)
    beserta analisis alasannya (`selection_analysis`). Planner tetap bisa mengganti metode
    lewat override append-only (`forecast_selection_service`). Tak ada klasifikasi kuadran
    (larangan #12).
  - Banyak produk (`run_forecast_for_products`): metode terbaik dipilih SEKALI untuk seluruh
    produk dari rata-rata pengujian seluruh produk (23 Nov 2026, permintaan user) —
    `selection.select_global_method`.
"""
import logging
from dataclasses import dataclass

import pandas as pd

from app.config import get_settings
from app.services.forecasting import registry
from app.services.forecasting.preprocessing import to_period_series
from app.services.forecasting.evaluation import mape_interpretation
from app.services.forecasting.selection import (
    DEFAULT_CRITERIA,
    method_label,
    select_best_method,
    select_global_method,
)
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
    # CR v3.6 §7.2 — alasan bahasa natural bila status gagal (None = sukses)
    status_reason: str | None = None
    # 23 Nov 2026 — analisis kenapa metode terpilih terbaik (mode otomatis); None = manual/gagal
    selection_analysis: dict | None = None


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
        # metode SETELAH run (mengganti metode terbaik pilihan sistem).
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


def _precheck(df: pd.DataFrame, requested_method: str | None) -> ForecastResultRecord | None:
    """INSUFFICIENT_DATA fail-fast (AGENTS §5 langkah 1); None = data cukup."""
    settings = get_settings()
    if df.empty or "date" not in df.columns or df["quantity"].dropna().empty:
        return ForecastResultRecord(
            status="INSUFFICIENT_DATA",
            status_reason="Belum ada histori demand (kolom actual) untuk produk ini.",
        )
    series = to_period_series(df)
    min_periods = settings.LSTM_MIN_PERIODS if requested_method == "lstm" else settings.BACKTEST_MIN_PERIODS
    if len(series) < min_periods:
        return ForecastResultRecord(
            status="INSUFFICIENT_DATA",
            status_reason=f"Histori {len(series)} periode, minimal {min_periods} periode"
            + (" untuk LSTM." if requested_method == "lstm" else "."),
        )
    return None


def _run_manual(df, horizon, method, enabled, options) -> ForecastResultRecord:
    if method not in enabled:
        raise UnsupportedForecastMethodError(f"Metode '{method}' tidak dikenal atau tidak aktif")
    forecast_fn = registry.MODEL_REGISTRY[method]
    try:
        result = forecast_fn(df, horizon, options=options)
    except Exception:  # TIDAK fallback di mode manual (AGENTS.md §5/#14)
        log.warning("Metode manual '%s' gagal", method, exc_info=True)
        return ForecastResultRecord(
            status="MODEL_SELECTION_FAILED",
            method_used=method,
            selection_mode="manual",
            status_reason=f"Metode {method} gagal dijalankan untuk data produk ini "
            "(mode manual tidak dialihkan ke metode lain).",
        )
    return _completed(method, "manual", result, [_candidate_row(method, result)])


_REASON_MAX = 200


def _failure_reason(exc: Exception) -> str:
    """Alasan bahasa natural kenapa satu metode gagal (24 Nov 2026) — ditampilkan di run supaya
    metode aktif yang gagal tidak hilang diam-diam dari perbandingan."""
    if isinstance(exc, ImportError) and (getattr(exc, "name", None) or "").split(".")[0] == "tensorflow":
        return (
            "TensorFlow belum terpasang di server (LSTM butuh TensorFlow, Python ≤ 3.13) — "
            "metode tidak bisa dijalankan."
        )
    text = f"{type(exc).__name__}: {exc}".strip()
    if len(text) > _REASON_MAX:
        text = text[: _REASON_MAX - 1] + "…"
    return f"Gagal saat backtest/fit — {text}"


def _evaluate_all(df, horizon, enabled, options) -> tuple[dict[str, EngineResult], dict[str, str]]:
    """Jalankan seluruh metode aktif; yang gagal dikecualikan (AGENTS §5 langkah 4) dan
    alasannya dicatat → (hasil per metode, {metode gagal: alasan})."""
    evaluated: dict[str, EngineResult] = {}
    failures: dict[str, str] = {}
    for method_name in sorted(enabled):  # sorted → ranking stabil saat seri
        forecast_fn = registry.MODEL_REGISTRY[method_name]
        try:
            evaluated[method_name] = forecast_fn(df, horizon, options=options)
        except Exception as exc:
            log.warning("Metode '%s' gagal saat backtest/fit, dikecualikan", method_name, exc_info=True)
            failures[method_name] = _failure_reason(exc)
    return evaluated, failures


def _failed_everywhere_line(failures: list[dict[str, str]]) -> str | None:
    """Metode aktif yang gagal di SELURUH produk dinilai — tidak terlihat di `excluded_methods`
    (yang hanya memuat metode gagal sebagian), jadi disebut eksplisit di alasan pemilihan."""
    common = set.intersection(*(set(f) for f in failures)) if failures else set()
    if not common:
        return None
    parts = [f"{method_label(m)} ({failures[0][m]})" for m in sorted(common)]
    return "Metode aktif yang gagal dijalankan di semua produk sehingga tidak dibandingkan: " + "; ".join(parts)


def _apply_global(
    evaluated: dict[str, EngineResult], failures: dict[str, str], outcome, metrics
) -> ForecastResultRecord:
    """Hasil satu produk memakai metode terbaik GLOBAL; bila metode itu gagal di produk ini →
    metode terbaik produk ini sendiri (dicatat di `selection_analysis.fallback_reason`)."""
    candidates = [_candidate_row(name, r) for name, r in evaluated.items()]
    ranks = {row["method"]: row for row in outcome.ranking}
    for c in candidates:
        row = ranks.get(c["method"])
        c.update({k: v for k, v in row.items() if k.startswith("rank")} if row else {"rank": None})
    candidates.sort(key=lambda c: (c["rank"] is None, c["rank"] or 0, c["method"]))

    analysis = outcome.to_dict()
    analysis["failed_methods"] = dict(failures)  # metode aktif yang gagal di produk ini + alasan
    chosen = outcome.best_method
    if chosen not in evaluated:
        own = select_best_method(candidates, metrics)
        chosen = own.best_method
        analysis["fallback_reason"] = (
            f"{method_label(outcome.best_method)} (terbaik untuk seluruh produk) gagal/tidak berlaku "
            f"untuk produk ini, sehingga dipakai {method_label(chosen)} — metode terbaik hasil "
            "pengujian produk ini sendiri."
        )

    record = _completed(chosen, "auto", evaluated[chosen], candidates)
    lead = analysis.get("fallback_reason") or outcome.summary
    record.explanation = f"{lead} {record.explanation}".strip()
    record.selection_analysis = analysis
    return record


def run_forecast_for_products(
    items: list[tuple[pd.DataFrame, EngineOptions | None]],
    horizon: int,
    requested_method: str | None = None,
    enabled_methods: set[str] | None = None,
    selection_metrics=DEFAULT_CRITERIA,
) -> list[ForecastResultRecord]:
    """Forecast banyak produk sekaligus. Mode otomatis: SATU metode terbaik untuk seluruh produk,
    dipilih dari RATA-RATA pengujian (MAD/MAPE/MFE) seluruh produk (23 Nov 2026, permintaan
    user). Produk gagal (INSUFFICIENT_DATA / semua metode gagal) tidak ikut dirata-rata.
    Urutan hasil = urutan `items`."""
    enabled = registry.get_enabled_methods(enabled_methods)
    if requested_method is not None and requested_method not in enabled:
        raise UnsupportedForecastMethodError(
            f"Metode '{requested_method}' tidak dikenal atau tidak aktif"
        )

    records: list[ForecastResultRecord | None] = []
    evaluations: list[tuple[dict[str, EngineResult], dict[str, str]] | None] = []
    for df, options in items:
        failed = _precheck(df, requested_method)
        if failed is not None:
            records.append(failed)
            evaluations.append(None)
        elif requested_method is not None:
            # ── MODE MANUAL ── langsung 1 metode, tanpa fallback
            records.append(_run_manual(df, horizon, requested_method, enabled, options))
            evaluations.append(None)
        else:
            evaluated, failures = _evaluate_all(df, horizon, enabled, options)
            if not evaluated:
                detail = "; ".join(f"{method_label(m)}: {r}" for m, r in sorted(failures.items()))
                records.append(
                    ForecastResultRecord(
                        status="MODEL_SELECTION_FAILED",
                        status_reason="Semua metode aktif gagal saat backtest/fit untuk data produk ini"
                        + (f" — {detail}" if detail else "."),
                    )
                )
                evaluations.append(None)
            else:
                records.append(None)
                evaluations.append((evaluated, failures))

    # ── MODE OTOMATIS: metode terbaik global dari rata-rata seluruh produk ──
    pending = [e for e in evaluations if e is not None]
    if pending:
        per_product = [[_candidate_row(name, r) for name, r in ev.items()] for ev, _ in pending]
        outcome = select_global_method(per_product, selection_metrics)
        line = _failed_everywhere_line([f for _, f in pending])
        if line:
            outcome.reasons.append(line)
        for i, e in enumerate(evaluations):
            if e is not None:
                records[i] = _apply_global(*e, outcome, selection_metrics)
    return records  # type: ignore[return-value]


def run_forecast_for_product(
    df: pd.DataFrame,
    horizon: int,
    requested_method: str | None = None,
    enabled_methods: set[str] | None = None,
    options: EngineOptions | None = None,
    selection_metrics=DEFAULT_CRITERIA,
) -> ForecastResultRecord:
    """Satu produk — kasus khusus `run_forecast_for_products` (rata-rata satu produk = produk itu)."""
    return run_forecast_for_products(
        [(df, options)],
        horizon,
        requested_method=requested_method,
        enabled_methods=enabled_methods,
        selection_metrics=selection_metrics,
    )[0]
