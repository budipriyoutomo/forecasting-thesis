"""
WarehouseService (v3.0 Fase 6, redesain 24 Agustus 2026) — kapasitas gudang per
PRODUK, angka bebas, docs/ARCHITECTURE.md §6.7.

Konfigurasi dulunya "luas gudang ÷ footprint palet"; sekarang planner mengisi
`capacity_qty` langsung per produk (satuan sama dengan unit produk). Validasi
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
    WarehouseConfigExistsError,
    WarehouseConfigNotFoundError,
)


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 4)))


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

    async def create_config(self, product_id: str, capacity_qty) -> WarehouseConfig:
        if await self._products.get_by_id(product_id) is None:
            raise ProductNotFoundError(f"Produk '{product_id}' tidak ditemukan.")
        if await self._config.get_by_product(product_id) is not None:
            raise WarehouseConfigExistsError("Produk ini sudah punya konfigurasi kapasitas.")
        config = WarehouseConfig(product_id=product_id, capacity_qty=_dec(capacity_qty))
        return await self._config.add(config)

    async def update_config(self, config_id: str, capacity_qty) -> WarehouseConfig:
        config = await self.get_config(config_id)
        config.capacity_qty = _dec(capacity_qty)
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
