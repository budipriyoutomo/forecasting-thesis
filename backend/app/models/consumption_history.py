"""
ORM model `consumption_history` — docs/ARCHITECTURE.md §4.

Riwayat konsumsi per material per tanggal, hasil parsing CSV upload. Dipakai
Fase 4 (forecasting) sebagai data historis.

Deviasi dari §4 (dicatat di RECONCILIATION.md #14): ditambah kolom `material_code`
dan `material_id` dibuat nullable. Alasan: satu file bisa memuat kode material
yang belum terdaftar di master data (Fase 2). Baris tetap disimpan (dengan
warning) tanpa memaksa auto-create material (yang akan jadi silent mutation
master data — dilarang AGENTS.md §6). `material_id` diisi bila kodenya cocok.
"""
import uuid
from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConsumptionHistory(Base):
    __tablename__ = "consumption_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    material_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True, index=True
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    upload_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("upload_sessions.id"), nullable=False, index=True
    )
