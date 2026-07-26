"""
ORM model `reorder_recommendations` — docs/ARCHITECTURE.md §4.

Hasil perhitungan safety stock & reorder point per material dalam satu run.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

REORDER_STATUSES = ("urgent", "safe", "overstock")


class ReorderRecommendation(Base):
    __tablename__ = "reorder_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True
    )
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    recommended_order_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # v3.0 — buffer stock, EOQ dinamis & total biaya (Bab III thesis)
    buffer_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    eoq_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    ordering_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    holding_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    total_inventory_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
