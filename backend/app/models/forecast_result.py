"""
ORM model `forecast_results` — docs/ARCHITECTURE.md §4.

Satu baris = hasil forecast satu material dalam satu run. Kolom `status`
ditambahkan (deviasi §4, dicatat RECONCILIATION #15) karena §8 secara eksplisit
menyebut `forecast_results.status` untuk menandai item yang gagal — kegagalan
satu material tidak menggagalkan run (AGENTS.md §5).
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

RESULT_STATUSES = ("COMPLETED", "INSUFFICIENT_DATA", "MODEL_SELECTION_FAILED")


class ForecastResult(Base):
    __tablename__ = "forecast_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPLETED")
    data_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    method_used: Mapped[str | None] = mapped_column(String(20), nullable=True)
    selection_mode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mase: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    forecast_data: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
