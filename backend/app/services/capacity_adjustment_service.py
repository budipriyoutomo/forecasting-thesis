"""
CapacityAdjustmentService (Fase 11.17, 19 Nov 2026) — loop validasi kapasitas gudang →
adjust SS & Buffer → ulang tahap 2 (MRP) → tahap 3 (proyeksi stok).
Keputusan: RECONCILIATION.md §"Loop Validasi Kapasitas Gudang → Adjust SS & Buffer".

Titik cek = STOK AKHIR periode skenario `proposed` (rumus thesis), per grup material:
  kelebihan grup = max_t (Σ stok akhir anggota[t] − kapasitas grup)

Usulan (simulasi di memori, TIDAK disimpan):
  1. Grup yang overload: service level SS diturunkan satu anak tangga
     (99 → 98 → 97 → 95 → 92,5 → 90 %, batas bawah 90%), ulang tahap 2→3.
  2. Sudah di batas bawah (atau SS tak bisa diturunkan, mis. SS manual) → Buffer anggota grup
     dipotong proporsional sebesar kelebihan, ulang tahap 2→3.
  3. Berhenti bila semua grup muat, tak ada lagi yang bisa diturunkan, atau MAX_ITERATIONS.
     Masih overload → `infeasible` + penyebab (stok awal / MOQ / cycle stock).

Planner menerima usulan atau mengisi angka custom (alasan wajib); keduanya disimpan
append-only per (run, material) di `capacity_adjustments` dan dipakai ReorderService pada
perencanaan berikutnya. Master data material tidak disentuh. Skenario baseline tidak
di-adjust. Overload tetap flag, bukan error (larangan #17).
"""
from statistics import NormalDist
from types import SimpleNamespace

from app.models.capacity_adjustment import CapacityAdjustment
from app.utils.exceptions import MaterialNotFoundError, OverrideReasonRequiredError

SERVICE_LEVEL_LADDER = (99.0, 98.0, 97.0, 95.0, 92.5, 90.0)
SERVICE_LEVEL_FLOOR = 90.0
MAX_ITERATIONS = 10
ADJUSTMENT_SOURCES = ("suggested", "custom", "reset")
OVERFLOW_CAUSES = ("opening_stock", "moq", "cycle_stock")  # "receipts" dihapus 20 Nov 2026
_EPS = 1e-6


def next_service_level(current: float) -> float | None:
    """Anak tangga service level berikutnya di bawah `current`; None bila sudah ≤ batas bawah."""
    for rung in SERVICE_LEVEL_LADDER:
        if rung < float(current) - _EPS:
            return rung
    return None


def _group_totals(rows, group_of: dict, capacity_by_group: dict) -> dict:
    """{grup: {periode: (Σ stok akhir, Σ pesanan)}} skenario proposed. Pesanan = kedatangan
    (hasil ROP, tiba di periode yang sama) — input kedatangan manual dihapus 20 Nov 2026."""
    totals: dict = {}
    for r in rows:
        if getattr(r, "scenario", "proposed") != "proposed":
            continue
        key = group_of.get(str(r.material_id))
        if not key or not capacity_by_group.get(key):
            continue
        ending, order = totals.setdefault(key, {}).get(r.period, (0.0, 0.0))
        totals[key][r.period] = (ending + float(r.ending_qty), order + float(getattr(r, "order_qty", 0) or 0))
    return totals


def group_overflow(rows, group_of: dict, capacity_by_group: dict) -> dict:
    """{grup: kelebihan terbesar (> 0)} — hanya grup yang melebihi kapasitas."""
    result = {}
    for key, periods in _group_totals(rows, group_of, capacity_by_group).items():
        excess = max(ending for ending, _ in periods.values()) - float(capacity_by_group[key])
        if excess > _EPS:
            result[key] = excess
    return result


def cut_buffers(buffers: dict, excess: float) -> dict:
    """Potong Buffer proporsional terhadap Buffer tiap material sebesar `excess` (min 0)."""
    total = sum(float(b) for b in buffers.values())
    if total <= 0:
        return {mid: float(b) for mid, b in buffers.items()}
    fraction = min(1.0, float(excess) / total)
    return {mid: max(0.0, float(b) * (1 - fraction)) for mid, b in buffers.items()}


def effective_service_level(safety_stock: float, sigma_lead_time: float) -> float | None:
    """α efektif (%) = Φ(SS ÷ σ_d·√L); None bila σ_d·√L = 0 (SS tak bergantung ketidakpastian)."""
    if float(sigma_lead_time) <= 0:
        return None
    return NormalDist().cdf(float(safety_stock) / float(sigma_lead_time)) * 100


def classify_overflow_cause(rows, group_of: dict, group: str, capacity: float, moq: dict) -> str:
    """Penyebab kelebihan di periode terburuk grup (informasi bagi planner)."""
    periods = _group_totals(rows, group_of, {group: capacity}).get(group, {})
    ordered = sorted(periods)
    worst = max(ordered, key=lambda p: periods[p][0])
    _, order = periods[worst]
    if order > _EPS:
        members = [
            r for r in rows
            if getattr(r, "scenario", "proposed") == "proposed"
            and r.period == worst and group_of.get(str(r.material_id)) == group
        ]
        for r in members:
            m = float(moq.get(str(r.material_id), 0) or 0)
            if m > 0 and 0 < float(r.order_qty) <= m + _EPS:
                return "moq"
        return "cycle_stock"
    if all(periods[p][1] <= _EPS for p in ordered if p <= worst):
        return "opening_stock"
    return "cycle_stock"


def active_adjustments(rows) -> dict:
    """{material_id: adjust} — baris terbaru per material; `reset` = kembali ke nilai sistem."""
    latest: dict = {}
    for row in sorted(rows, key=lambda r: r.created_at, reverse=True):
        latest.setdefault(str(row.material_id), row)
    return {mid: row for mid, row in latest.items() if row.source != "reset"}


def as_adjustment(service_level_pct=None, safety_stock=None, buffer_stock=None, source="suggested"):
    return SimpleNamespace(
        service_level_pct=service_level_pct, safety_stock=safety_stock, buffer_stock=buffer_stock, source=source
    )


DEFAULT_SERVICE_LEVEL_PCT = 95.0
DEFAULT_SUGGESTED_REASON = "Menerima usulan sistem — stok proyeksi melebihi kapasitas gudang"
DEFAULT_RESET_REASON = "Kembali ke nilai sistem (adjust kapasitas dibatalkan)"


def _f(value) -> float:
    return float(value) if value is not None else 0.0


def _opt(value) -> float | None:
    return float(value) if value is not None else None


def _snapshot(rec) -> dict:
    return {
        "safety_stock": str(rec.safety_stock),
        "buffer_stock": str(rec.buffer_stock) if rec.buffer_stock is not None else None,
        "reorder_point": str(rec.reorder_point),
        "service_level_effective": (
            str(rec.service_level_effective) if getattr(rec, "service_level_effective", None) is not None else None
        ),
        "adjustment_source": getattr(rec, "adjustment_source", None),
    }


class CapacityAdjustmentReader:
    """Adjust yang berlaku per material — dipakai ReorderService (tanpa siklus dependensi)."""

    def __init__(self, repo):
        self._repo = repo

    async def adjustments_by_material(self, run_id: str) -> dict:
        return active_adjustments(await self._repo.list_by_run(run_id))


class CapacityAdjustmentService:
    def __init__(self, repo, reorder, projection, settings=None, materials=None, factory=None):
        self._repo = repo
        self._reorder = reorder  # ReorderService (compute_for_run / list_for_run)
        self._projection = projection  # StockProjectionService (compute_for_run / capacity_context)
        self._settings = settings  # ForecastSettingsService → target service level
        self._materials = materials  # SS manual tidak diturunkan lewat service level
        self._factory = factory or CapacityAdjustment

    # ── usulan (simulasi, tidak disimpan) ──

    async def suggest(self, user_id: str, run_id: str) -> dict:
        persisted = await self._reorder.list_for_run(user_id, run_id)
        current_stock = {
            str(r.material_id): float(r.current_stock_used)
            for r in persisted
            if getattr(r, "stock_source", None) == "request" and getattr(r, "current_stock_used", None) is not None
        }
        target = await self._settings.service_level_pct() if self._settings else DEFAULT_SERVICE_LEVEL_PCT
        group_of, capacity = await self._projection.capacity_context()

        async def stage(sim: dict):
            recs = await self._reorder.compute_for_run(user_id, run_id, current_stock, adjustments=dict(sim))
            rows = await self._projection.compute_for_run(user_id, run_id, recs=recs, scenarios=("proposed",))
            return recs, rows

        base_recs, rows = await stage({})
        initial = group_overflow(rows, group_of, capacity)
        result = {"status": "within_capacity", "target_service_level_pct": float(target), "iterations": 0,
                  "groups": [], "items": []}
        if not initial:
            return result

        manual = await self._manual_ss_materials(base_recs)
        level = {g: float(target) for g in initial}
        sim: dict = {}
        recs, over, iterations = base_recs, initial, 0
        while over and iterations < MAX_ITERATIONS:
            by_mid = {str(r.material_id): r for r in recs}
            changed = False
            for group, excess in over.items():
                members = [m for m in by_mid if group_of.get(m) == group]
                reducible = [m for m in members if m not in manual and _f(by_mid[m].safety_stock) > 0]
                rung = next_service_level(level[group])
                if rung is not None and reducible:
                    level[group] = rung
                    for m in reducible:
                        prev = sim.get(m)
                        sim[m] = as_adjustment(service_level_pct=rung, buffer_stock=prev.buffer_stock if prev else None)
                    changed = True
                    continue
                buffers = {m: _f(by_mid[m].buffer_stock) for m in members}
                if sum(buffers.values()) > 0:
                    for m, b in cut_buffers(buffers, excess).items():
                        prev = sim.get(m)
                        sim[m] = as_adjustment(service_level_pct=prev.service_level_pct if prev else None, buffer_stock=b)
                    changed = True
            if not changed:
                break
            iterations += 1
            recs, rows = await stage(sim)
            over = group_overflow(rows, group_of, capacity)

        base = {str(r.material_id): r for r in base_recs}
        final = {str(r.material_id): r for r in recs}
        moq = {mid: _f(getattr(r, "moq_used", 0)) for mid, r in final.items()}
        result.update(status="infeasible" if over else "adjusted", iterations=iterations)
        for group, excess in initial.items():
            infeasible = group in over
            result["groups"].append({
                "group": group,
                "capacity_qty": float(capacity[group]),
                "excess_before": excess,
                "excess_after": over.get(group, 0.0),
                "service_level_pct": level[group],
                "status": "infeasible" if infeasible else "adjusted",
                "cause": classify_overflow_cause(rows, group_of, group, capacity[group], moq) if infeasible else None,
            })
        for mid, adj in sim.items():
            before, after = base[mid], final[mid]
            result["items"].append({
                "material_id": mid,
                "group": group_of.get(mid),
                "safety_stock_before": _f(before.safety_stock),
                "safety_stock_after": _f(after.safety_stock),
                "buffer_stock_before": _f(before.buffer_stock),
                "buffer_stock_after": _f(after.buffer_stock),
                "reorder_point_before": _f(before.reorder_point),
                "reorder_point_after": _f(after.reorder_point),
                "service_level_before": _opt(getattr(before, "service_level_effective", None)),
                "service_level_after": _opt(getattr(after, "service_level_effective", None)),
                "service_level_pct": adj.service_level_pct,
            })
        return result

    async def _manual_ss_materials(self, recs) -> set[str]:
        if self._materials is None:
            return set()
        manual = set()
        for r in recs:
            material = await self._materials.get_by_id(str(r.material_id))
            if material is not None and getattr(material, "manual_safety_stock", None) is not None:
                manual.add(str(r.material_id))
        return manual

    # ── simpan / reset / baca (append-only) ──

    async def save(self, user_id: str, run_id: str, source: str, items: list[dict], reason: str | None):
        recs = {str(r.material_id): r for r in await self._reorder.list_for_run(user_id, run_id)}
        reason = (reason or "").strip()
        if source == "custom" and not reason:
            raise OverrideReasonRequiredError("Alasan wajib diisi untuk adjust custom.")
        reason = reason or DEFAULT_SUGGESTED_REASON
        rows = []
        for item in items:
            rec = recs.get(str(item["material_id"]))
            if rec is None:
                raise MaterialNotFoundError("Material tidak ada di rekomendasi reorder run ini.")
            rows.append(self._factory(
                run_id=rec.run_id, material_id=rec.material_id, user_id=user_id, source=source,
                service_level_pct=item.get("service_level_pct"),
                safety_stock=item.get("safety_stock"), buffer_stock=item.get("buffer_stock"),
                previous_value=_snapshot(rec), reason=reason,
            ))
        return await self._repo.add_all(rows)

    async def reset(self, user_id: str, run_id: str, reason: str | None) -> int:
        recs = {str(r.material_id): r for r in await self._reorder.list_for_run(user_id, run_id)}
        active = active_adjustments(await self._repo.list_by_run(run_id))
        rows = [
            self._factory(
                run_id=adj.run_id, material_id=adj.material_id, user_id=user_id, source="reset",
                service_level_pct=None, safety_stock=None, buffer_stock=None,
                previous_value=_snapshot(recs[mid]) if mid in recs else None,
                reason=(reason or "").strip() or DEFAULT_RESET_REASON,
            )
            for mid, adj in active.items()
        ]
        if rows:
            await self._repo.add_all(rows)
        return len(rows)

    async def list_active(self, user_id: str, run_id: str) -> list:
        await self._reorder.list_for_run(user_id, run_id)  # cek run & akses
        return list(active_adjustments(await self._repo.list_by_run(run_id)).values())

    async def history(self, user_id: str, run_id: str) -> list:
        await self._reorder.list_for_run(user_id, run_id)
        return await self._repo.list_by_run(run_id)
