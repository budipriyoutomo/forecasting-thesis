"""
ORM model proyeksi stok material per run (Fase 11.6, 30 Oktober 2026) — tahap 3 thesis.

Satu baris = satu material × satu periode × satu skenario (proposed = forecast,
baseline = planning perusahaan). Utilisasi = stok ÷ kapasitas material × 100%.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StockProjection(Base):
    __tablename__ = "stock_projections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False
    )
    scenario: Mapped[str] = mapped_column(String(10), nullable=False, default="proposed")
    period: Mapped[date] = mapped_column(Date, nullable=False)
    opening_qty: Mapped[float] = mapped_column(Float, nullable=False)
    receipt_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    usage_qty: Mapped[float] = mapped_column(Float, nullable=False)
    order_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    ending_qty: Mapped[float] = mapped_column(Float, nullable=False)
    shortage_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    capacity_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    utilization_opening_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    utilization_ending_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_within_capacity: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
