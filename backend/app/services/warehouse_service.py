"""
WarehouseService (v3.0 Fase 6, redesain 24 Agustus 2026) — kapasitas gudang per
PRODUK, docs/ARCHITECTURE.md §6.7.

Konfigurasi dulunya "luas gudang ÷ footprint palet"; sejak 24 Agustus planner mengisi
kapasitas langsung per produk. Sejak Fase 10 (2 Oktober 2026) input-nya pallet, dus,
atau kombinasi; `capacity_qty` (unit produk) & `uom` dihitung server lewat
`compute_effective_capacity` (RECONCILIATION §"Konsolidasi Master Data"). Validasi
dijalankan per produk: kebutuhan = total qty forecast produk di satu run,
dibandingkan `capacity_qty` konfigurasinya. Melebihi kapasitas BUKAN error —
hanya flag `is_within_capacity` (larangan #17), keputusan tetap di planner.
"""
from dataclasses import dataclass
from decimal import Decimal

from app.models.warehouse import WarehouseConfig, WarehouseValidation
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    ProductNotFoundError,
    WarehouseCapacityInvalidError,
    WarehouseConfigExistsError,
    WarehouseConfigNotFoundError,
)

CAPACITY_MODES = ("PALLET", "DUS", "COMBINED")
# Unit produk yang dianggap sudah "per dus" — kapasitas dus dibandingkan langsung.
DUS_LIKE_UNITS = {"DUS", "KARTON", "BOX", "CTN"}


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 4)))


@dataclass
class CapacityInput:
    capacity_mode: str
    pallet_qty: float = 0
    dus_qty: float = 0
    dus_per_pallet: float | None = None
    pcs_per_dus: float | None = None


def is_dus_like(unit: str) -> bool:
    return unit.strip().upper() in DUS_LIKE_UNITS


def uses_pallet(mode: str) -> bool:
    return mode in ("PALLET", "COMBINED")


def uses_dus(mode: str) -> bool:
    return mode in ("DUS", "COMBINED")


def compute_effective_capacity(inp: CapacityInput, product_unit: str) -> tuple[float, float]:
    """
    Return (capacity_dus, capacity_qty dalam unit produk).
      capacity_dus = pallet_qty × dus_per_pallet (mode PALLET/COMBINED) + dus_qty (mode DUS/COMBINED)
      capacity_qty = capacity_dus (unit dus-like) atau capacity_dus × pcs_per_dus (unit lain)
    Input tak lengkap/negatif/kapasitas 0 → WarehouseCapacityInvalidError.
    """
    if inp.capacity_mode not in CAPACITY_MODES:
        raise WarehouseCapacityInvalidError(f"Mode kapasitas '{inp.capacity_mode}' tidak dikenal.")
    if float(inp.pallet_qty or 0) < 0 or float(inp.dus_qty or 0) < 0:
        raise WarehouseCapacityInvalidError("Jumlah pallet/dus tidak boleh negatif.")

    capacity_dus = 0.0
    if uses_pallet(inp.capacity_mode):
        if inp.dus_per_pallet is None or float(inp.dus_per_pallet) <= 0:
            raise WarehouseCapacityInvalidError("Isi dus per pallet (> 0) untuk mode pallet/kombinasi.")
        capacity_dus += float(inp.pallet_qty or 0) * float(inp.dus_per_pallet)
    if uses_dus(inp.capacity_mode):
        capacity_dus += float(inp.dus_qty or 0)
    if capacity_dus <= 0:
        raise WarehouseCapacityInvalidError("Kapasitas efektif harus lebih dari 0.")

    if is_dus_like(product_unit):
        return capacity_dus, capacity_dus
    if inp.pcs_per_dus is None or float(inp.pcs_per_dus) <= 0:
        raise WarehouseCapacityInvalidError(
            f"Unit produk '{product_unit}' bukan dus — isi isi per dus (> 0)."
        )
    return capacity_dus, capacity_dus * float(inp.pcs_per_dus)


def capacity_dus_of(config) -> float:
    """Kapasitas dalam dus dari baris tersimpan (tidak dipersist, Fase 10)."""
    total = float(config.dus_qty or 0) if uses_dus(config.capacity_mode) else 0.0
    if uses_pallet(config.capacity_mode):
        total += float(config.pallet_qty or 0) * float(config.dus_per_pallet or 0)
    return total


@dataclass
class ProductCapacityResult:
    product_id: str
    required_qty: float
    capacity_qty: float
    is_within_capacity: bool


@dataclass
class WarehouseCapacityResult:
    is_within_capacity: bool
    details: list[ProductCapacityResult]


def validate_capacity(
    configs: list[WarehouseConfig], forecast_qty_by_product: dict[str, float]
) -> WarehouseCapacityResult:
    """
    Per produk yang dikonfigurasi DAN punya forecast di run ini:
      is_within_capacity_produk = required_qty (Σ forecast) <= capacity_qty.
    Agregat `is_within_capacity` = True hanya bila SEMUA entri muat. Produk tanpa
    config atau tanpa forecast di run ini dilewati (tak bisa dibandingkan).
    """
    details: list[ProductCapacityResult] = []
    for config in configs:
        pid = str(config.product_id)
        required = forecast_qty_by_product.get(pid)
        if required is None:
            continue
        capacity = float(config.capacity_qty)
        details.append(
            ProductCapacityResult(
                product_id=pid,
                required_qty=float(required),
                capacity_qty=capacity,
                is_within_capacity=required <= capacity,
            )
        )
    return WarehouseCapacityResult(
        is_within_capacity=all(d.is_within_capacity for d in details),
        details=details,
    )


class WarehouseService:
    def __init__(self, config_repo, validation_repo, forecast_repo, products):
        self._config = config_repo
        self._validations = validation_repo
        self._forecast = forecast_repo
        self._products = products

    async def list_configs(self) -> list[WarehouseConfig]:
        return await self._config.list()

    async def get_config(self, config_id: str) -> WarehouseConfig:
        config = await self._config.get_by_id(config_id)
        if config is None:
            raise WarehouseConfigNotFoundError("Konfigurasi gudang tidak ditemukan.")
        return config

    async def create_config(self, product_id: str, inp: CapacityInput) -> WarehouseConfig:
        product = await self._products.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(f"Produk '{product_id}' tidak ditemukan.")
        if await self._config.get_by_product(product_id) is not None:
            raise WarehouseConfigExistsError("Produk ini sudah punya konfigurasi kapasitas.")
        config = WarehouseConfig(product_id=product_id)
        apply_capacity(config, inp, product.unit)
        return await self._config.add(config)

    async def update_config(self, config_id: str, inp: CapacityInput) -> WarehouseConfig:
        config = await self.get_config(config_id)
        product = await self._products.get_by_id(str(config.product_id))
        if product is None:
            raise ProductNotFoundError(f"Produk '{config.product_id}' tidak ditemukan.")
        apply_capacity(config, inp, product.unit)
        return await self._config.save(config)

    async def delete_config(self, config_id: str) -> None:
        config = await self.get_config(config_id)
        await self._config.delete(config)

    async def validate_for_run(self, user_id: str, run_id: str) -> WarehouseValidation:
        await self._require_run(user_id, run_id)
        configs = await self._config.list()
        if not configs:
            raise WarehouseConfigNotFoundError("Belum ada konfigurasi kapasitas gudang.")

        results = await self._forecast.list_results(run_id)
        forecast_qty_by_product: dict[str, float] = {}
        for r in results:
            if r.status == "COMPLETED" and r.forecast_data:
                pid = str(r.product_id)
                forecast_qty_by_product[pid] = sum(p["value"] for p in r.forecast_data)

        result = validate_capacity(configs, forecast_qty_by_product)
        validation = WarehouseValidation(
            run_id=run_id,
            is_within_capacity=result.is_within_capacity,
            details=[
                {
                    "product_id": d.product_id,
                    "required_qty": d.required_qty,
                    "capacity_qty": d.capacity_qty,
                    "is_within_capacity": d.is_within_capacity,
                }
                for d in result.details
            ],
        )
        return await self._validations.replace_for_run(str(run_id), validation)

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run


def apply_capacity(config, inp: CapacityInput, product_unit: str) -> None:
    """Validasi + hitung kapasitas, lalu tulis ke `config` dengan field tak relevan dinormalisasi."""
    _, capacity_qty = compute_effective_capacity(inp, product_unit)
    pallet = uses_pallet(inp.capacity_mode)
    config.capacity_mode = inp.capacity_mode
    config.pallet_qty = _dec(inp.pallet_qty or 0) if pallet else _dec(0)
    config.dus_per_pallet = _dec(inp.dus_per_pallet) if pallet else None
    config.dus_qty = _dec(inp.dus_qty or 0) if uses_dus(inp.capacity_mode) else _dec(0)
    config.pcs_per_dus = None if is_dus_like(product_unit) else _dec(inp.pcs_per_dus)
    config.capacity_qty = _dec(capacity_qty)
    config.uom = product_unit
