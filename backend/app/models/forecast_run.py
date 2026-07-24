"""
ORM model `forecast_runs` — docs/ARCHITECTURE.md §4.

Satu run mencakup BANYAK material sekaligus (bukan 1 run = 1 item), sesuai
realita upload PPIC. Status: PENDING / PROCESSING / COMPLETED / FAILED.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

RUN_STATUSES = ("PENDING", "PROCESSING", "COMPLETED", "FAILED")


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_unit: Mapped[str] = mapped_column(String(10), nullable=False, default="days")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
