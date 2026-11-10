"""
ForecastSelectionService (Fase 11.15, 10 Nov 2026) — planner memilih metode per produk.

Mode otomatis tidak lagi memilih pemenang (RECONCILIATION §"Fase 11.15"): seluruh metode
aktif disimpan di `candidates_evaluated` beserta deret forecast-nya, `forecast_results.
method_used`/`forecast_data` NULL. Planner memilih metode lewat OVERRIDE append-only
(`target_type = forecast_result`, `new_value = {"method_used": ...}`, alasan wajib) —
hasil asli tidak pernah diubah (AGENTS.md §5/§6).

Metode yang berlaku per hasil:
  1. override terbaru yang metodenya ada di kandidat (dengan deret forecast), lalu
  2. `method_used` hasil itu sendiri (mode manual / run lama sebelum Fase 11.15).
Tanpa keduanya → `PENDING_SELECTION`: hasil tidak punya `forecast_data`, sehingga Reorder,
Proyeksi Stok, Cost, Validasi Gudang, Metrik Inventori & export melewatinya.

Service ini juga adapter baca untuk hilir: `list_results(run_id)` mengembalikan view hasil
dengan pilihan sudah diterapkan; method repository lain diteruskan apa adanya. Service
hilir TIDAK menafsirkan pilihan sendiri.
"""
from dataclasses import dataclass
from types import SimpleNamespace

from app.services.forecast_run_service import forecast_summary
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    OverrideReasonRequiredError,
    OverrideTargetNotFoundError,
    UnsupportedForecastMethodError,
)

TARGET_TYPE = "forecast_result"
SELECTED = "SELECTED"
PENDING = "PENDING_SELECTION"


def _selectable(result) -> dict[str, dict]:
    """{metode: kandidat} yang bisa dipilih — hanya kandidat yang membawa deret forecast."""
    if getattr(result, "status", None) != "COMPLETED":
        return {}
    return {c["method"]: c for c in (result.candidates_evaluated or []) if c.get("forecast")}


class SelectedResult:
    """View read-only atas `ForecastResult` dengan metode berlaku diterapkan.

    Atribut yang tidak di-override diteruskan ke objek asli (ORM tidak dimutasi)."""

    def __init__(self, result, override=None):
        self._result = result
        self.selection_override = None
        candidate = _selectable(result).get((override.new_value or {}).get("method_used")) if override else None
        if candidate is not None:
            self.selection_override = override
            fdata = candidate["forecast"]
            self.method_used = candidate["method"]
            self.forecast_data = fdata
            self.metrics = forecast_summary([SimpleNamespace(**p) for p in fdata])
            for key in ("mad", "mfe", "mse", "mape", "mase", "explanation", "feature_importance", "hyperparameters"):
                setattr(self, key, candidate.get(key))
        if result.status != "COMPLETED":
            self.selection_status = None
        elif self.method_used and self.forecast_data:
            self.selection_status = SELECTED
        else:
            self.selection_status = PENDING

    @property
    def selection_reason(self) -> str | None:
        return self.selection_override.reason if self.selection_override else None

    @property
    def selected_at(self):
        return getattr(self.selection_override, "created_at", None) if self.selection_override else None

    @property
    def selected_by(self):
        return getattr(self.selection_override, "user_id", None) if self.selection_override else None

    def __getattr__(self, name):
        return getattr(self._result, name)


def _latest_valid(result, overrides) -> object | None:
    """Override terbaru (urutan repo: terbaru dulu) yang metodenya bisa dipilih."""
    selectable = _selectable(result)
    for ov in overrides:
        if ov.target_type == TARGET_TYPE and (ov.new_value or {}).get("method_used") in selectable:
            return ov
    return None


@dataclass
class RunSelectionOutcome:
    n_selected: int
    skipped_product_ids: list[str]
    results: list[SelectedResult]


class ForecastSelectionService:
    def __init__(self, forecast_repo, override_repo, override_service):
        self._repo = forecast_repo
        self._overrides = override_repo
        self._override_service = override_service

    # ── Adapter baca untuk hilir ──

    async def list_results(self, run_id: str) -> list[SelectedResult]:
        by_target: dict[str, list] = {}
        for ov in await self._overrides.list_by_context(str(run_id)):
            if ov.target_type == TARGET_TYPE:
                by_target.setdefault(str(ov.target_id), []).append(ov)
        return [
            SelectedResult(r, _latest_valid(r, by_target.get(str(r.id), [])))
            for r in await self._repo.list_results(run_id)
        ]

    async def list_results_for_product(self, product_id: str) -> list[SelectedResult]:
        return [await self._view(r) for r in await self._repo.list_results_for_product(product_id)]

    def __getattr__(self, name):
        return getattr(self._repo, name)

    # ── Pilihan planner ──

    async def select(self, user_id: str, result_id: str, method: str, reason: str) -> SelectedResult:
        if not reason or not reason.strip():
            raise OverrideReasonRequiredError("Alasan memilih metode wajib diisi.")
        result = await self._repo.get_result(result_id)
        if result is None:
            raise OverrideTargetNotFoundError("Hasil forecast tidak ditemukan.")
        await self._require_run(user_id, str(result.run_id))
        if method not in _selectable(result):
            raise UnsupportedForecastMethodError(
                f"Metode '{method}' tidak tersedia untuk hasil forecast ini."
            )
        await self._record(user_id, result, method, reason)
        return await self._view(result)

    async def select_for_run(self, user_id: str, run_id: str, method: str, reason: str) -> RunSelectionOutcome:
        if not reason or not reason.strip():
            raise OverrideReasonRequiredError("Alasan memilih metode wajib diisi.")
        await self._require_run(user_id, run_id)
        results = await self._repo.list_results(run_id)
        targets = [r for r in results if method in _selectable(r)]
        if not targets:
            raise UnsupportedForecastMethodError(
                f"Metode '{method}' tidak tersedia di produk mana pun pada run ini."
            )
        for r in targets:
            await self._record(user_id, r, method, reason)
        target_ids = {str(r.id) for r in targets}
        return RunSelectionOutcome(
            n_selected=len(targets),
            skipped_product_ids=[str(r.product_id) for r in results if str(r.id) not in target_ids],
            results=await self.list_results(run_id),
        )

    async def _record(self, user_id: str, result, method: str, reason: str):
        await self._override_service.create(
            user_id, TARGET_TYPE, str(result.id), {"method_used": method}, reason
        )

    async def _view(self, result) -> SelectedResult:
        overrides = await self._overrides.list_by_target(str(result.id))
        return SelectedResult(result, _latest_valid(result, overrides))

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._repo.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
