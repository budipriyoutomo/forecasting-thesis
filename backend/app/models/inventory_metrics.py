"""
ORM model `inventory_metrics` (v3.0 Fase 7) — docs/ARCHITECTURE.md §4.

Evaluasi kinerja inventory per run: service level, fill rate, stock out rate,
inventory turnover (rumus di RECONCILIATION §Fase 7). Kolom `scope`
(`baseline` / `forecastiq`) net-new di luar skema §4 — memisahkan kinerja
kondisi EXISTING perusahaan (actual vs planning) dari kinerja ForecastIQ
(actual vs forecast), supaya dashboard bisa membandingkan keduanya.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

METRIC_SCOPES = ("baseline", "forecastiq")


class InventoryMetric(Base):
    __tablename__ = "inventory_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)  # product / material
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="baseline")
    service_level: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    fill_rate: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    stock_out_rate: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    inventory_turnover: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
