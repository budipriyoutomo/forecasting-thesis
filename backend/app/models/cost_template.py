"""
ORM model template biaya (Fase 10, 2 Oktober 2026) — docs/ARCHITECTURE.md §4/§6.8,
RECONCILIATION §"Konsolidasi Master Data".

`cost_templates`      : S (`ordering_cost`) & H (`holding_cost`, isian manual) untuk
                        EOQ/TIC. Boleh banyak template, maksimal satu `is_active`
                        (partial unique index). Tanpa template aktif → fallback env.
`cost_template_items` : overhead bulanan (listrik, dll) & aset penyimpanan (pallet,
                        rak, alat handling) — hanya referensi untuk *saran H*, tidak
                        dipakai EOQ langsung.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CostTemplate(Base):
    __tablename__ = "cost_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordering_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    holding_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # selectin: aman untuk async (tanpa lazy load implisit); delete-orphan → PUT
    # yang mengganti seluruh daftar item ikut menghapus item lama.
    items: Mapped[list["CostTemplateItem"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CostTemplateItem.position",
    )


class CostTemplateItem(Base):
    __tablename__ = "cost_template_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cost_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # urutan tampil
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # OVERHEAD | STORAGE_ASSET
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    salvage_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    useful_life_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=1)

    template: Mapped[CostTemplate] = relationship(back_populates="items")
