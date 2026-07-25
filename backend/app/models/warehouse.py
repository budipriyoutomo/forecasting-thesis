"""
ORM model kapasitas gudang (v3.0 Fase 6) — docs/ARCHITECTURE.md §4/§6.7.

`warehouse_config`  : parameter fisik gudang (luas, dimensi palet) per kategori.
`warehouse_validations` : hasil validasi per run — apakah rekomendasi inventory
muat secara fisik. Melebihi kapasitas BUKAN error, hanya flag `is_within_capacity`
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
    category: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, default="packaging")
    warehouse_area_m2: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    pallet_dimension: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {length, width, height}
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
    total_pallet_capacity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_pallet_required: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    is_within_capacity: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
