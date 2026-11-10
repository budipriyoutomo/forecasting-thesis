"""
ORM model Pengaturan Forecast (Fase 11.2a, 29 Oktober 2026) — docs/REVISI_V2.md §6.1
Keputusan #6, RECONCILIATION §"Rekonsiliasi v3.2".

`forecast_settings`: SATU baris global (id = 1, dijaga CHECK). Menyimpan pengaturan
metode forecast sebagai master data — bukan env — supaya admin bisa mengubahnya dari
UI. Belum ada baris → default di kode (semua metrik tampil, seluruh metode aktif).

Fase 11.15 (10 Nov 2026): `ranking_metric` (metrik penentu pemenang) dihapus — sistem tidak
lagi memilih pemenang. `display_metrics` = metrik yang DITAMPILKAN di hasil forecast.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DISPLAY_METRICS = ("mad", "mfe", "mse", "mape")  # urutan baku tampilan


class ForecastSetting(Base):
    __tablename__ = "forecast_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_forecast_settings_singleton"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    # Fase 11.15 — checkbox metrik yang tampil di hasil forecast. NULL = semua (DISPLAY_METRICS).
    display_metrics: Mapped[list[str] | None] = mapped_column(ARRAY(String(10)), nullable=True)
    # Metode aktif Comparative Selection (pengganti env FORECAST_ENGINES_ENABLED).
    # NULL = belum diatur → seluruh metode di MODEL_REGISTRY.
    enabled_methods: Mapped[list[str] | None] = mapped_column(ARRAY(String(50)), nullable=True)
    # Opsi engine (Fase 11.2). es_alpha_grid NULL = grid thesis (types.THESIS_ALPHA_GRID).
    es_alpha_grid: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)
    es_alpha_metric: Mapped[str] = mapped_column(String(10), nullable=False, default="mad")
    ml_grid_search: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ml_winsorize: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Perencanaan persediaan (Fase 11.4) — bukan env (permintaan user 30 Okt 2026).
    service_level_pct: Mapped[float] = mapped_column(Float, nullable=False, default=95.0)
    eoq_method: Mapped[str] = mapped_column(String(10), nullable=False, default="classic")
    # Fase 11.9 (v3.3) — sumber tunggal titik & qty pesan untuk Reorder + Proyeksi Stok.
    rop_formula: Mapped[str] = mapped_column(String(20), nullable=False, default="with_buffer")
    order_qty_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="order_up_to")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
