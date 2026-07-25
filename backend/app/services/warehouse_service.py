"""
WarehouseService (v3.0 Fase 6) — kapasitas gudang berbasis palet & validasi
apakah rekomendasi inventory muat fisik (docs/ARCHITECTURE.md §6.7).

Fungsi murni (`compute_*`, `validate_capacity`) diverifikasi manual (AGENTS.md §3).
Melebihi kapasitas BUKAN error — hanya flag `is_within_capacity` (larangan #17).
"""
from dataclasses import dataclass
from decimal import Decimal

from app.models.warehouse import WarehouseConfig, WarehouseValidation
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    WarehouseConfigNotFoundError,
)


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 4)))


@dataclass
class WarehouseCapacityResult:
    total_pallet_capacity: int
    total_pallet_required: float
    is_within_capacity: bool


def compute_pallet_capacity(warehouse_area_m2: float, pallet_dimension: dict) -> int:
    """Jumlah palet muat = Luas Gudang ÷ footprint palet (panjang × lebar)."""
    footprint = float(pallet_dimension["length"]) * float(pallet_dimension["width"])
    if footprint <= 0:
        return 0
    return int(float(warehouse_area_m2) // footprint)


def compute_material_capacity(pallet_capacity: int, qty_per_pallet: float) -> float:
    """Kapasitas material (unit) = jumlah palet × qty material per palet."""
    return float(pallet_capacity) * float(qty_per_pallet)


def _required_units(rec) -> float:
    ss = float(rec.safety_stock or 0)
    buffer = float(getattr(rec, "buffer_stock", 0) or 0)
    eoq = float(getattr(rec, "eoq_qty", 0) or 0)
    return ss + buffer + eoq


def validate_capacity(
    recommendations, materials_by_id: dict, warehouse_area_m2: float, pallet_dimension: dict
) -> WarehouseCapacityResult:
    """
    Total palet dibutuhkan = Σ_material (safety_stock + buffer + eoq) ÷ qty_per_pallet.
    Muat bila total ≤ kapasitas palet gudang. Material tanpa qty_per_pallet dilewati
    (tak bisa dihitung kebutuhan paletnya).
    """
    pallet_capacity = compute_pallet_capacity(warehouse_area_m2, pallet_dimension)
    total_required = 0.0
    for rec in recommendations:
        material = materials_by_id.get(str(rec.material_id))
        qpp = float(material.qty_per_pallet) if material and material.qty_per_pallet else 0.0
        if qpp <= 0:
            continue
        total_required += _required_units(rec) / qpp
    return WarehouseCapacityResult(
        total_pallet_capacity=pallet_capacity,
        total_pallet_required=total_required,
        is_within_capacity=total_required <= pallet_capacity,
    )


class WarehouseService:
    def __init__(self, config_repo, validation_repo, reorder_repo, materials, forecast_repo):
        self._config = config_repo
        self._validations = validation_repo
        self._reorder = reorder_repo
        self._materials = materials
        self._forecast = forecast_repo

    async def get_config(self, category: str = "packaging") -> WarehouseConfig:
        config = await self._config.get_by_category(category)
        if config is None:
            raise WarehouseConfigNotFoundError("Konfigurasi gudang belum diatur.")
        return config

    async def upsert_config(self, category: str, area_m2, pallet_dimension: dict) -> WarehouseConfig:
        config = await self._config.get_by_category(category)
        if config is None:
            config = WarehouseConfig(
                category=category, warehouse_area_m2=_dec(area_m2), pallet_dimension=pallet_dimension
            )
            return await self._config.add(config)
        config.warehouse_area_m2 = _dec(area_m2)
        config.pallet_dimension = pallet_dimension
        return await self._config.save(config)

    async def validate_for_run(
        self, user_id: str, run_id: str, category: str = "packaging"
    ) -> WarehouseValidation:
        await self._require_run(user_id, run_id)
        config = await self.get_config(category)

        recs = await self._reorder.list_by_run(run_id)
        materials_by_id: dict = {}
        for rec in recs:
            mid = str(rec.material_id)
            if mid not in materials_by_id:
                materials_by_id[mid] = await self._materials.get_by_id(mid)

        result = validate_capacity(
            recs, materials_by_id, float(config.warehouse_area_m2), config.pallet_dimension
        )
        validation = WarehouseValidation(
            run_id=run_id,
            total_pallet_capacity=_dec(result.total_pallet_capacity),
            total_pallet_required=_dec(result.total_pallet_required),
            is_within_capacity=result.is_within_capacity,
        )
        await self._validations.replace_for_run(str(run_id), validation)
        return validation

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
