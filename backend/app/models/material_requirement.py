"""
ORM model `material_requirements` (v3.0) — docs/ARCHITECTURE.md §4.

Hasil breakdown BOM per run: total kebutuhan tiap material dari forecast seluruh
produk terkait (`forecast_qty`), plus standar/aktual pemakaian & buffer stock %
(mengantisipasi waste produksi, Bab III thesis).
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MaterialRequirement(Base):
    __tablename__ = "material_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True
    )
    forecast_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    standard_usage_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    actual_usage_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    buffer_stock_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
