"""
ORM model `capacity_adjustments` (Fase 11.17, 19 Nov 2026) — adjust SS & Buffer per
(run, material) agar stok proyeksi muat kapasitas gudang grup material.

APPEND-ONLY (pola sama dengan `overrides`): yang berlaku = baris terbaru per (run, material);
`source = reset` mengembalikan material ke nilai sistem. Master data material TIDAK diubah.
`previous_value` = snapshot nilai rekomendasi saat adjust disimpan (audit).
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CapacityAdjustment(Base):
    __tablename__ = "capacity_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # suggested | custom | reset
    service_level_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    safety_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    buffer_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    previous_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
