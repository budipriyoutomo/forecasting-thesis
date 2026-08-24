"""
ORM model kapasitas gudang (v3.0 Fase 6, redesain 24 Agustus 2026) —
docs/ARCHITECTURE.md §4/§6.7.

`warehouse_config`  : kapasitas per PRODUK, angka bebas (unit produk, bukan palet).
                      Input planner langsung — tidak diturunkan dari luas gudang ×
                      dimensi palet lagi (keputusan user: free input). `uom` juga
                      free input teks (mis. "Dus", "Pcs", "Karton") — TIDAK ada
                      tabel master UOM (redesain 24 Agustus 2026).
`warehouse_validations` : hasil validasi per run — per produk, apakah forecast qty
muat kapasitasnya. Melebihi kapasitas BUKAN error, hanya flag `is_within_capacity`
(keputusan tetap di planner, AGENTS.md larangan #17).
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WarehouseConfig(Base):
    __tablename__ = "warehouse_config"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), unique=True, nullable=False, index=True
    )
    capacity_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    uom: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class WarehouseValidation(Base):
    __tablename__ = "warehouse_validations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id"), nullable=False, index=True
    )
    # True hanya bila SEMUA produk yang dikonfigurasi muat kapasitasnya.
    is_within_capacity: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # [{product_id, required_qty, capacity_qty, is_within_capacity}] — satu entri
    # per produk yang punya WarehouseConfig DAN forecast COMPLETED di run ini.
    details: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
