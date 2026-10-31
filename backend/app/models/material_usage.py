"""
ORM model pemakaian aktual material (Fase 11.1, 30 Oktober 2026) — REVISI_V2 §3.8.

Satu baris = pemakaian aktual vs standar satu material pada satu periode (opsional per
produk). Standar = output produksi × BOM, atau diisi langsung saat upload. Dasar faktor
waste → buffer stock.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MaterialUsage(Base):
    __tablename__ = "material_usage_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    production_output: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    standard_usage: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    actual_usage: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
