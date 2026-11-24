"""
Perbandingan hasil forecast run PER METODE — format thesis "Part 1 = Forecast" (CR v3.7).

Fungsi murni read-only atas hasil run yang SUDAH tersimpan (`candidates_evaluated` tiap produk);
tidak menjalankan engine dan tidak mengubah apa pun. Untuk tiap metode:
  (a) matriks hasil ramalan varian × periode, (b) pengujian MAD · MAPE · MFE + baris Average,
lalu kesimpulan metode terbaik level run.

Aturan (RECONCILIATION §"CR v3.7"):
  - Urutan metode = `THESIS_METHOD_ORDER`; metode lain di belakang (abjad). Metode tanpa
    kandidat sama sekali di run → tidak muncul, KECUALI metode aktif yang gagal (tercatat di
    `selection_analysis.failed_methods`, 24 Nov 2026) → tampil dengan baris FAILED + `reason`.
  - Status baris: OK · FAILED (metode gagal/dikecualikan, atau produk gagal) · NO_SERIES
    (run sebelum Fase 11.15: metrik ada, deret tidak disimpan).
  - Average = rata-rata aritmetika atas varian yang metodenya berhasil; MFE BERTANDA.
  - Metode terbaik level run = seleksi GLOBAL yang sama dengan yang dipakai run
    (`selection_analysis` scope "global" tersimpan; run lama/manual → `select_global_method`).
    Tidak ada logika peringkat di modul ini (AGENTS #20).
"""
from __future__ import annotations

from collections.abc import Sequence

from app.services.forecasting.selection import (
    DEFAULT_CRITERIA,
    PRIORITY,
    _finite,
    _mean,
    method_label,
    select_global_method,
)

THESIS_METHOD_ORDER = [
    "random_forest",
    "lstm",
    "xgboost",
    "moving_average",
    "exponential_smoothing",
]

_METRICS = ("mad", "mape", "mfe")  # urutan kolom sketsa thesis
_RANK_KEYS = ("method", "rank", "rank_mad", "rank_mape", "rank_mfe", "mad", "mape", "mfe", "n_products")


def _completed(result) -> bool:
    return getattr(result, "status", None) == "COMPLETED" and bool(getattr(result, "candidates_evaluated", None))


def _analysis(result) -> dict | None:
    sa = (getattr(result, "metrics", None) or {}).get("selection_analysis")
    return sa if isinstance(sa, dict) else None


def run_criteria(results) -> Sequence[str]:
    """Snapshot urutan prioritas run (`selection_analysis.criteria`); fallback DEFAULT_CRITERIA."""
    return next((sa["criteria"] for sa in map(_analysis, results) if sa and sa.get("criteria")), DEFAULT_CRITERIA)


def _failed_methods(result) -> dict[str, str]:
    """{metode aktif yang gagal: alasan} tersimpan di `selection_analysis` (sejak 24 Nov 2026)."""
    failed = (_analysis(result) or {}).get("failed_methods")
    return failed if isinstance(failed, dict) else {}


def _ordered_methods(results) -> list[str]:
    present = {c["method"] for r in results if _completed(r) for c in r.candidates_evaluated}
    # Metode aktif yang gagal di SEMUA produk tetap tampil (status FAILED + alasan), bukan hilang.
    present |= {m for r in results if _completed(r) for m in _failed_methods(r)}
    thesis = [m for m in THESIS_METHOD_ORDER if m in present]
    return thesis + sorted(present - set(THESIS_METHOD_ORDER))


def _row(product_id: str, candidate: dict | None, reason: str | None = None) -> dict:
    if candidate is None:
        return {
            "product_id": product_id, "status": "FAILED", "forecast": {}, "total": None,
            "mad": None, "mape": None, "mfe": None,
            "reason": reason,  # None = alasan tidak tercatat (run lama / produk gagal)
        }
    series = candidate.get("forecast") or []
    forecast = {str(p["date"])[:10]: float(p["value"]) for p in series}
    return {
        "product_id": product_id,
        "status": "OK" if series else "NO_SERIES",
        "forecast": forecast,
        "total": sum(forecast.values()) if forecast else None,  # kolom Total matriks
        **{m: _finite(candidate.get(m)) for m in _METRICS},
        "reason": None,
    }


def _average(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["status"] != "FAILED"]
    return {**{m: _mean(r[m] for r in ok) for m in _METRICS}, "n": len(ok), "n_total": len(rows)}


def _run_selection(results, criteria: Sequence[str]) -> dict | None:
    done = [r for r in results if _completed(r)]
    if not done:
        return None
    stored = next((sa for sa in map(_analysis, done) if sa and sa.get("scope") == "global"), None)
    analysis = stored or select_global_method([r.candidates_evaluated for r in done], criteria).to_dict()
    excluded = list(analysis.get("excluded_methods") or [])
    n_common = int(analysis.get("n_products") or 0)
    return {
        "best_method": analysis["best_method"],
        "criteria": list(analysis.get("criteria") or criteria),
        "ranking_basis": "common" if excluded or n_common < len(done) else "all",
        "n_common": n_common,
        "n_completed": len(done),
        "excluded_methods": excluded,
        "ranking": [{k: row.get(k) for k in _RANK_KEYS if k in row} for row in analysis.get("ranking") or []],
        "decided_by": analysis.get("decided_by"),
        "summary": analysis.get("summary") or "",
        "reasons": list(analysis.get("reasons") or []),
    }


def _product_method(result) -> dict:
    done = getattr(result, "status", None) == "COMPLETED"
    return {
        "product_id": str(result.product_id),
        "status": result.status,
        "system_method": getattr(result, "system_method", result.method_used) if done else None,
        "method_used": result.method_used if done else None,
        "is_overridden": getattr(result, "selection_override", None) is not None,
    }


def build_method_comparison(results: list, criteria: Sequence[str]) -> dict:
    """`results` = hasil run lewat `ForecastSelectionService.list_results` (urutan dipertahankan)."""
    methods = []
    for method in _ordered_methods(results):
        rows = []
        for r in results:
            cands = {c["method"]: c for c in r.candidates_evaluated} if _completed(r) else {}
            rows.append(_row(str(r.product_id), cands.get(method), _failed_methods(r).get(method)))
        methods.append({"method": method, "label": method_label(method), "rows": rows, "average": _average(rows)})

    periods = sorted({d for m in methods for row in m["rows"] for d in row["forecast"]})
    run_selection = _run_selection(results, criteria)
    return {
        "periods": periods,
        "criteria": run_selection["criteria"] if run_selection else [m for m in PRIORITY if m in set(criteria)],
        "methods": methods,
        "run_selection": run_selection,
        "product_methods": [_product_method(r) for r in results],
    }
