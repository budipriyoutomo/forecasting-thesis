"""
ORM model komponen material — BOM level 2+ (Fase 11.3, 30 Oktober 2026), REVISI_V2 §3.4.

`material_components`: material induk (mis. Bottle White) tersusun dari komponen
(mis. Preform White). Keputusan #4: Bottle DIBELI JADI → komponen hanya informasi,
tidak ikut breakdown kebutuhan/EOQ/kapasitas. Siklus dicegah di service.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MaterialComponent(Base):
    __tablename__ = "material_components"
    __table_args__ = (
        UniqueConstraint("parent_material_id", "component_material_id", name="uq_material_components_pair"),
        CheckConstraint("parent_material_id <> component_material_id", name="ck_material_components_not_self"),
        CheckConstraint("qty_per_unit > 0", name="ck_material_components_qty_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    parent_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False
    )
    qty_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
