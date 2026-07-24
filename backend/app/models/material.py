"""
ORM model `materials` — docs/ARCHITECTURE.md §4.

Master data material (raw material) untuk PPIC: identitas + parameter yang
dibutuhkan reorder point & safety stock (lead time, MOQ, safety stock manual).
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    moq: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    manual_safety_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
