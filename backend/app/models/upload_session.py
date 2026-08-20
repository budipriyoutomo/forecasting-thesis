"""
ORM model `upload_sessions` — docs/ARCHITECTURE.md §4.

Satu baris = satu upload CSV konsumsi. Menyimpan ringkasan hasil validasi
(preview, warnings, jumlah baris/material) + lokasi file di object storage. `expires_at`
dipakai cron cleanup untuk menghapus file temp yang belum divalidasi (§7).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Status siklus hidup upload (docs/ARCHITECTURE.md §4).
UPLOAD_STATUSES = ("pending", "validated", "failed", "expired")


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_kb: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_products_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preview_data: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
