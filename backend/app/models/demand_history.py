"""
ORM model `demand_history` (v3.0) — docs/ARCHITECTURE.md §4.

Revisi dari `consumption_history` v2.0: menyimpan 3 seri paralel per produk jadi
per periode (bulan) — `forecast_existing` (metode existing perusahaan), `planning`
(rencana produksi setelah judgment planner), `actual` (realisasi = target/label ML).
Struktur ini mengikuti data riil `Simulasi Thesis.xlsx` sheet "Bab I Plan vs Forecast"
dan dipakai dashboard untuk mengukur gap akurasi ForecastIQ vs kondisi existing.

`product_id` nullable + `product_code` snapshot (pola RECONCILIATION #14): histori
tidak putus bila master data produk berubah/dihapus setelah upload.
"""
import uuid
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemandHistory(Base):
    __tablename__ = "demand_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    product_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    period: Mapped[date_type] = mapped_column(Date, nullable=False)  # biasanya awal bulan
    forecast_existing: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    planning: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    actual: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)  # target/label ML
    upload_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("upload_sessions.id"), nullable=False, index=True
    )
