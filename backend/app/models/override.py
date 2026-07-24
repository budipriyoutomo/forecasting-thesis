"""
ORM model `overrides` — docs/ARCHITECTURE.md §4, AGENTS.md §5 (non-negotiable).

APPEND-ONLY audit trail: setiap override planner disimpan sebagai baris BARU,
tidak pernah menimpa hasil forecast/reorder asli. `reason` WAJIB (NOT NULL) —
`OVERRIDE_REASON_REQUIRED` bila kosong.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

OVERRIDE_TARGET_TYPES = ("forecast_result", "reorder_recommendation")


class Override(Base):
    __tablename__ = "overrides"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # FK dinamis (bisa ke forecast_results atau reorder_recommendations) — tidak
    # dipasang ForeignKey DB karena target-nya polimorfik.
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    previous_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
