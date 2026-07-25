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
    # v3.0: forecasting objeknya PRODUK jadi. `material_id` legacy dipertahankan
    # nullable (jalur v2.0) sampai cutover Fase 9; run v3.0 mengisi `product_id`.
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPLETED")
    data_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # legacy v2.0 (kuadran), unused v3.0
    method_used: Mapped[str | None] = mapped_column(String(30), nullable=True)  # v3.0: moving_average/.../lstm
    selection_mode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    candidates_evaluated: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # v3.0 comparative, semua kandidat
    mad: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    mfe: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    mse: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    mape: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    mase: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)  # opsional (COMPUTE_MASE)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    forecast_data: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
