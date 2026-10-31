"""
ORM model variabel eksternal (Fase 11.2b, 30 Oktober 2026) — Keputusan #7,
docs/REVISI_V2.md §3.6g/§6.1, RECONCILIATION §"Rekonsiliasi v3.2".

`external_variables`       : master dinamis (musim, cuaca/temperatur, harga, promo, event, ...).
                             `scope` global = satu deret untuk semua produk; product = per SKU.
                             Hanya `is_active` yang dipakai engine ML sebagai fitur.
`external_variable_values` : nilai per periode (upload). product_id NULL untuk scope global.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

VALUE_TYPES = ("numeric", "flag")
SCOPES = ("global", "product")


class ExternalVariable(Base):
    __tablename__ = "external_variables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # nama fitur ML
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value_type: Mapped[str] = mapped_column(String(10), nullable=False, default="numeric")
    scope: Mapped[str] = mapped_column(String(10), nullable=False, default="global")
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ExternalVariableValue(Base):
    __tablename__ = "external_variable_values"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    variable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_variables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
