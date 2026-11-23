"""
Pemilihan metode terbaik otomatis — mode otomatis forecast run (23 Nov 2026).

Membalik Fase 11.15 ("sistem tidak memilih pemenang") atas permintaan user: forecast run
tidak lagi meminta planner memilih metode; sistem menjalankan seluruh metode aktif lalu
memilih yang terbaik berdasarkan **pengujian peramalan** (metrik yang dicentang di master data
Pengaturan Forecast) dan menjelaskan alasannya. Planner tetap bisa mengganti metode lewat
override (AGENTS.md §5 "Planner Override").

Aturan = URUTAN PRIORITAS pengujian (keputusan user 23 Nov 2026), fungsi murni & deterministik
— RECONCILIATION §"Metode Terbaik Otomatis":
  1) MAD terkecil menang.
  2) MAD seri → MAPE terkecil.
  3) MAD & MAPE seri → |MFE| terkecil (bias paling dekat nol).
  Seri dibandingkan pada presisi simpan (6 desimal, `Numeric(18,6)`); seri total → nama metode.
  Metrik yang tidak dicentang dilewati (urutan tetap). Nilai tak terdefinisi (None/NaN/inf,
  mis. MAPE saat seluruh aktual uji nol) → kalah di metrik itu.
Peringkat per metrik (`rank_<metrik>`, kompetisi 1, 1, 3) tetap dicatat sebagai informasi.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.services.forecasting.evaluation import mape_interpretation

# Urutan prioritas pengujian (keputusan user 23 Nov 2026): 1) MAD, 2) MAPE, 3) MFE.
PRIORITY = ("mad", "mape", "mfe")
DEFAULT_CRITERIA = PRIORITY
_TIE_DECIMALS = 6

METHOD_LABELS = {
    "moving_average": "Moving Average",
    "exponential_smoothing": "Exponential Smoothing",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
    "lstm": "LSTM",
}

_METRIC_LABELS = {"mad": "MAD", "mfe": "MFE", "mse": "MSE", "mape": "MAPE"}


def method_label(method: str) -> str:
    return METHOD_LABELS.get(method, method)


def _finite(value) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _score(candidate: dict, metric: str) -> float | None:
    """Nilai pembanding (kecil = baik), dibulatkan ke presisi simpan. MFE → |MFE|."""
    v = _finite(candidate.get(metric))
    if v is None:
        return None
    return round(abs(v) if metric == "mfe" else v, _TIE_DECIMALS)


def _key(score: float | None) -> float:
    return math.inf if score is None else score


def _competition_rank(scores: list[float | None]) -> list[int]:
    """Peringkat kompetisi (1, 1, 3); None → setelah seluruh nilai terdefinisi."""
    defined = sorted(s for s in scores if s is not None)
    last = len(defined) + 1
    return [defined.index(s) + 1 if s is not None else last for s in scores]


def _fmt(value: float | None, metric: str) -> str:
    if value is None:
        return "tidak terdefinisi"
    text = f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if metric == "mape":
        return f"{text}%"
    if metric == "mfe" and value > 0:
        return f"+{text}"
    return text


def _priority_text(criteria: list[str]) -> str:
    return ", ".join(
        f"{i}) {_METRIC_LABELS[m]}" + (" (|MFE|)" if m == "mfe" else "") for i, m in enumerate(criteria, start=1)
    )


@dataclass
class SelectionOutcome:
    best_method: str
    criteria: list[str]  # urutan prioritas yang dipakai
    ranking: list[dict]  # terurut: peringkat akhir 1 dulu
    summary: str
    reasons: list[str] = field(default_factory=list)
    # Metrik yang memisahkan pemenang dari peringkat 2; None = satu kandidat / seri total.
    decided_by: str | None = None

    def to_dict(self) -> dict:
        """Aman untuk JSONB (tanpa NaN/inf)."""
        return {
            "best_method": self.best_method,
            "criteria": list(self.criteria),
            "decided_by": self.decided_by,
            "ranking": self.ranking,
            "summary": self.summary,
            "reasons": list(self.reasons),
        }


def select_best_method(candidates: list[dict], metrics) -> SelectionOutcome:
    if not candidates:
        raise ValueError("Tidak ada kandidat untuk dipilih.")
    criteria = [m for m in PRIORITY if m in set(metrics or ())] or list(PRIORITY)

    scores = {m: [_score(c, m) for c in candidates] for m in criteria}
    ranks = {m: _competition_rank(scores[m]) for m in criteria}

    rows = []
    for i, c in enumerate(candidates):
        row = {"method": c["method"]}
        for m in criteria:
            row[f"rank_{m}"] = ranks[m][i]
        for m in ("mad", "mfe", "mape"):
            row[m] = _finite(c.get(m))
        row["_key"] = tuple(_key(scores[m][i]) for m in criteria)
        rows.append(row)

    rows.sort(key=lambda r: (r["_key"], r["method"]))
    decided_by = None
    if len(rows) > 1:
        for idx, m in enumerate(criteria):
            if rows[0]["_key"][idx] != rows[1]["_key"][idx]:
                decided_by = m
                break
    for pos, row in enumerate(rows, start=1):
        row["rank"] = pos
        del row["_key"]

    best = rows[0]
    summary, reasons = _explain(best, rows, criteria, decided_by)
    return SelectionOutcome(best["method"], criteria, rows, summary, reasons, decided_by)


def _explain(best: dict, rows: list[dict], criteria: list[str], decided_by: str | None) -> tuple[str, list[str]]:
    name = method_label(best["method"])
    prio = _priority_text(criteria)
    if len(rows) == 1:
        summary = (
            f"{name} dipilih karena menjadi satu-satunya metode yang berhasil diuji "
            "(metode lain gagal atau tidak aktif). Hasil pengujian di bawah tetap menjadi acuan kualitasnya."
        )
        return summary, [_quality_line(best)]

    runner = rows[1]
    runner_name = method_label(runner["method"])
    first = _METRIC_LABELS[criteria[0]]
    summary = (
        f"{name} dipilih sebagai metode terbaik dari {len(rows)} metode yang diuji dengan holdout "
        f"backtest. Penentuan memakai urutan prioritas pengujian: {prio} — metrik berikutnya hanya "
        "dipakai bila metrik sebelumnya seri. "
    )
    if decided_by is None:
        summary += (
            f"Seluruh metrik pengujian {name} seri dengan {runner_name}; {name} diambil berdasarkan urutan nama."
        )
    elif decided_by == criteria[0]:
        summary += (
            f"{name} memiliki {first} terkecil ({_fmt(best[criteria[0]], criteria[0])}, "
            f"dibanding {runner_name} {_fmt(runner[criteria[0]], criteria[0])})."
        )
    else:
        tied = criteria[: criteria.index(decided_by)]
        label = _METRIC_LABELS[decided_by]
        summary += (
            f"{' dan '.join(_METRIC_LABELS[m] for m in tied)} seri dengan {runner_name}, sehingga {label} "
            f"menentukan: {name} {_fmt(best[decided_by], decided_by)} vs {runner_name} "
            f"{_fmt(runner[decided_by], decided_by)}."
        )

    reasons = [_metric_line(best, rows, m, criteria) for m in criteria]
    reasons.append(_quality_line(best))
    reasons.append(f"Pembanding terdekat (peringkat 2): {runner_name}.")
    return summary, reasons


def _metric_line(best: dict, rows: list[dict], metric: str, criteria: list[str]) -> str:
    label = _METRIC_LABELS[metric]
    prio = criteria.index(metric) + 1
    value = _fmt(best[metric], metric)
    rank = best[f"rank_{metric}"]
    others = [r for r in rows if r["method"] != best["method"] and r[metric] is not None]
    if metric == "mfe":
        bias = best["mfe"]
        arah = (
            "tanpa bias" if not bias
            else "cenderung under-forecast" if bias > 0
            else "cenderung over-forecast"
        )
        head = f"Prioritas {prio} — {label} {value} ({arah}), peringkat {rank} dari {len(rows)}"
    else:
        head = f"Prioritas {prio} — {label} {value}, peringkat {rank} dari {len(rows)}"
    if not others:
        return head + "."
    key = (lambda r: abs(r["mfe"])) if metric == "mfe" else (lambda r: r[metric])
    leader = min(others, key=key)
    if rank == 1:
        return head + f"; terdekat {method_label(leader['method'])} {_fmt(leader[metric], metric)}."
    return head + (
        f"; terbaik di metrik ini {method_label(leader['method'])} {_fmt(leader[metric], metric)} — "
        "prioritasnya lebih rendah, tidak mengubah keputusan."
    )


def _quality_line(best: dict) -> str:
    mape = best["mape"]
    if mape is None:
        return "MAPE tidak terdefinisi (seluruh aktual periode uji bernilai nol) — gunakan MAD sebagai acuan."
    return f"Interpretasi MAPE {_fmt(mape, 'mape')}: {mape_interpretation(mape)} (skala Lewis, 1982)."
