"""
Pydantic schemas untuk endpoint forecast — docs/ARCHITECTURE.md §5/§6.8.
"""
from pydantic import BaseModel, Field


class ForecastRunRequest(BaseModel):
    """POST /api/v1/forecast/runs — banyak PRODUK jadi sekaligus (§6.6).

    `method` None/absen → mode otomatis: semua metode aktif dijalankan, sistem memilih yang
    terbaik dari pengujian peramalan (23 Nov 2026). UI tidak lagi menawarkan pilihan metode.
    `method` diisi → mode manual (dipertahankan untuk kompatibilitas API).
    """

    product_ids: list[str] = Field(min_length=1)
    horizon: int = Field(gt=0)
    horizon_unit: str = "days"
    method: str | None = None


class ForecastPointOut(BaseModel):
    date: str
    value: float
    lower: float
    upper: float


class HistoryPointOut(BaseModel):
    date: str
    value: float


class ForecastRunSummary(BaseModel):
    run_id: str
    status: str  # PENDING / PROCESSING / COMPLETED / FAILED
    horizon: int
    horizon_unit: str
    n_products: int
    n_completed: int
    n_failed: int
    n_pending_selection: int = 0  # Fase 11.15 — COMPLETED tapi metode belum dipilih planner


class ForecastResultOut(BaseModel):
    id: str
    product_id: str
    status: str  # COMPLETED / INSUFFICIENT_DATA / MODEL_SELECTION_FAILED
    # Fase 11.15 — metode yang BERLAKU (pilihan planner / mode manual / run lama); None = belum dipilih
    method_used: str | None = None
    selection_status: str | None = None  # SELECTED / PENDING_SELECTION; None = hasil gagal
    selection_reason: str | None = None
    selected_at: str | None = None
    selection_mode: str | None = None
    mad: float | None = None
    mfe: float | None = None
    mse: float | None = None
    mape: float | None = None
    mase: float | None = None
    candidates_evaluated: list | None = None
    explanation: str | None = None
    forecast: list[ForecastPointOut] = []
    metrics: dict | None = None
    feature_importance: dict | None = None  # Fase 11.2 — RF/XGB
    hyperparameters: dict | None = None
    # CR v3.6 §7.1/§7.2 — snapshot histori aktual (≤24 periode terakhir) & alasan gagal.
    # Dibaca dari `metrics` JSONB; run sebelum v3.6 → [] / None.
    history: list[HistoryPointOut] = []
    status_reason: str | None = None
    # 23 Nov 2026 — analisis kenapa sistem memilih metode terbaik (mode otomatis):
    # {best_method, criteria, ranking[], summary, reasons[]}. None = manual / run lama / gagal.
    selection_analysis: dict | None = None


class ForecastRunListItem(BaseModel):
    """GET /forecast/runs — satu baris daftar run (CR v3.6 §1: counts additive)."""

    run_id: str
    status: str
    horizon: int
    horizon_unit: str
    created_at: str | None = None
    created_by: str | None = None
    n_products: int = 0
    n_completed: int = 0
    n_failed: int = 0
    n_pending_selection: int = 0
    has_planning: bool = False


class MethodSelectionRequest(BaseModel):
    """POST /forecast/results/{id}/selection & /forecast/runs/{id}/selection (Fase 11.15).

    Pilihan disimpan sebagai override append-only — alasan wajib (OVERRIDE_REASON_REQUIRED)."""

    method: str = Field(min_length=1)
    reason: str = ""


class RunSelectionOut(BaseModel):
    n_selected: int
    skipped_product_ids: list[str]  # tidak punya metode itu / hasil gagal
    results: list[ForecastResultOut]


# ── CR v3.7 — GET /forecast/runs/{id}/method-comparison (format thesis per metode) ──


class MethodComparisonRow(BaseModel):
    product_id: str
    status: str  # OK / FAILED (metode gagal atau produk gagal) / NO_SERIES (run lama tanpa deret)
    forecast: dict[str, float] = {}  # periode (YYYY-MM-DD) → qty
    total: float | None = None  # Σ deret horizon (kolom Total); None bila tidak ada deret
    mad: float | None = None
    mape: float | None = None
    mfe: float | None = None


class MethodAverage(BaseModel):
    mad: float | None = None
    mape: float | None = None
    mfe: float | None = None  # rata-rata BERTANDA
    n: int  # varian yang metodenya berhasil
    n_total: int


class MethodComparisonMethod(BaseModel):
    method: str
    label: str
    rows: list[MethodComparisonRow]
    average: MethodAverage


class RunRankingRow(BaseModel):
    method: str
    rank: int
    rank_mad: int | None = None
    rank_mape: int | None = None
    rank_mfe: int | None = None
    mad: float | None = None
    mape: float | None = None
    mfe: float | None = None
    n_products: int | None = None


class RunSelection(BaseModel):
    """Metode terbaik level run = seleksi GLOBAL yang dipakai run (bukan dihitung ulang di FE)."""

    best_method: str
    criteria: list[str]
    ranking_basis: str  # "all" | "common" (ada metode dikeluarkan / irisan varian)
    n_common: int
    n_completed: int
    excluded_methods: list[str] = []
    ranking: list[RunRankingRow]
    decided_by: str | None = None
    summary: str = ""
    reasons: list[str] = []


class ProductMethodRow(BaseModel):
    product_id: str
    status: str
    system_method: str | None = None  # pilihan sistem (global / fallback)
    method_used: str | None = None  # metode berlaku (setelah penggantian planner)
    is_overridden: bool = False


class MethodComparisonOut(BaseModel):
    run_id: str
    periods: list[str]
    criteria: list[str]
    methods: list[MethodComparisonMethod]
    run_selection: RunSelection | None = None
    product_methods: list[ProductMethodRow]
