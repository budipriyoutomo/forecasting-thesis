"""
OverrideService — planner override + audit trail (Fase 6, AGENTS.md §5).

Non-negotiable:
- `reason` WAJIB → `OVERRIDE_REASON_REQUIRED` bila kosong.
- APPEND-ONLY: setiap override jadi baris baru di tabel `overrides`. Data asli
  (forecast_result / reorder_recommendation) TIDAK pernah diubah/dihapus — service
  ini hanya membaca snapshot lama (previous_value) lalu menyimpan entri baru.
- Target polimorfik di-resolve lewat `resolvers` (dict target_type → fungsi async
  yang mengembalikan objek target atau None).

v3.3 (Fase 11.14): override dicatat beserta konteks (run_id, material_id) dari targetnya.
Rekomendasi reorder di-generate ulang dengan id baru, jadi riwayat & qty override yang
BERLAKU dicari per (run, material): override terbaru yang `recommended_order_qty`-nya angka.
Qty override ditampilkan di tabel Reorder & dipakai Proyeksi Stok (pesanan periode pertama);
angka sistem tetap tersimpan apa adanya.
"""
from decimal import Decimal

from app.models.override import Override
from app.utils.exceptions import OverrideReasonRequiredError, OverrideTargetNotFoundError


def _json_safe(value):
    return str(value) if isinstance(value, Decimal) else value


def _snapshot_forecast_result(obj) -> dict:
    return {
        "method_used": obj.method_used,
        "selection_mode": obj.selection_mode,
        "mase": _json_safe(obj.mase),
        "forecast_data": obj.forecast_data,
        "metrics": obj.metrics,
    }


def _snapshot_reorder(obj) -> dict:
    return {
        "safety_stock": _json_safe(obj.safety_stock),
        "reorder_point": _json_safe(obj.reorder_point),
        "recommended_order_qty": _json_safe(obj.recommended_order_qty),
        "status": obj.status,
    }


SNAPSHOT_BUILDERS = {
    "forecast_result": _snapshot_forecast_result,
    "reorder_recommendation": _snapshot_reorder,
}


def _as_qty(value) -> float | None:
    try:
        qty = float(value)
    except (TypeError, ValueError):
        return None
    return qty if qty >= 0 else None


def latest_reorder_qty(overrides) -> dict:
    """{material_id: (qty, override)} — override terbaru per material yang qty-nya angka ≥ 0."""
    result: dict = {}
    for ov in sorted(overrides, key=lambda o: o.created_at, reverse=True):
        mid = getattr(ov, "material_id", None)
        if mid is None or str(mid) in result:
            continue
        qty = _as_qty((ov.new_value or {}).get("recommended_order_qty"))
        if qty is not None:
            result[str(mid)] = (qty, ov)
    return result


class OverrideService:
    def __init__(self, override_repo, resolvers: dict):
        self._repo = override_repo
        self._resolvers = resolvers

    async def create(
        self, user_id: str, target_type: str, target_id: str, new_value: dict, reason: str
    ) -> Override:
        if not reason or not reason.strip():
            raise OverrideReasonRequiredError("Alasan override wajib diisi.")

        resolver = self._resolvers.get(target_type)
        target = await resolver(target_id) if resolver else None
        if target is None:
            raise OverrideTargetNotFoundError("Target override tidak ditemukan.")

        previous_value = SNAPSHOT_BUILDERS[target_type](target)
        override = Override(
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            previous_value=previous_value,
            new_value=new_value,
            reason=reason.strip(),
            run_id=getattr(target, "run_id", None),
            material_id=getattr(target, "material_id", None) if target_type == "reorder_recommendation" else None,
        )
        return await self._repo.add(override)

    async def list_for_target(self, target_id: str) -> list[Override]:
        return await self._repo.list_by_target(target_id)

    async def list_for_reorder(self, run_id: str, material_id: str) -> list[Override]:
        return await self._repo.list_by_context(str(run_id), str(material_id))

    async def reorder_qty_by_material(self, run_id: str) -> dict:
        """{material_id: (qty, override)} qty override reorder yang berlaku untuk satu run."""
        rows = [o for o in await self._repo.list_by_context(str(run_id)) if o.target_type == "reorder_recommendation"]
        return latest_reorder_qty(rows)
