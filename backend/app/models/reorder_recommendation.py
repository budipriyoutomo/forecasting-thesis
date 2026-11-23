"""
ORM model `reorder_recommendations` — docs/ARCHITECTURE.md §4.

Hasil perhitungan safety stock & reorder point per material dalam satu run.
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

REORDER_STATUSES = ("urgent", "safe", "overstock")


class ReorderRecommendation(Base):
    __tablename__ = "reorder_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forecast_runs.id"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True
    )
    safety_stock: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    recommended_order_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # v3.0 — buffer stock, EOQ dinamis & total biaya (Bab III thesis)
    buffer_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    # Fase 11.1: Σ aktual ÷ Σ standar pemakaian; NULL = belum ada data pemakaian aktual.
    waste_factor: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    eoq_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    ordering_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    holding_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    total_inventory_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    # Fase 11.4 — EOQ klasik vs dinamis per material (REVISI_V2 §3.5)
    eoq_method: Mapped[str | None] = mapped_column(String(10), nullable=True)  # classic | dynamic
    item_status: Mapped[str | None] = mapped_column(String(30), nullable=True)  # COMPLETED | MISSING_*
    annual_demand: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit_price_used: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    holding_rate_used: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    # Fase 11.5 — stok yang dipakai & sumbernya (snapshot ERP | request fallback)
    current_stock_used: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    stock_source: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Fase 11.9 (v3.3) — kebijakan pesan yang dipakai (audit) + input yang dibutuhkan
    # Proyeksi Stok agar memakai titik & qty pesan yang sama. NULL = baris sebelum v3.3.
    rop_formula_used: Mapped[str | None] = mapped_column(String(20), nullable=True)  # standard | with_buffer
    order_qty_policy_used: Mapped[str | None] = mapped_column(String(20), nullable=True)  # eoq | order_up_to
    order_up_to_level: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    moq_used: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    # Fase 11.17 — adjust kapasitas gudang (capacity_adjustments). Nilai SISTEM sebelum adjust
    # (NULL = tidak di-adjust) dipakai audit & skenario baseline; α efektif = Φ(SS ÷ σ_d·√L).
    safety_stock_system: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    buffer_stock_system: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    service_level_effective: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    adjustment_source: Mapped[str | None] = mapped_column(String(10), nullable=True)  # suggested | custom
    # 23 Nov 2026 — INPUT perhitungan yang dipakai (audit & tampilan "Perencanaan persediaan"):
    # μ/σ kebutuhan per periode, hari per periode, lead time (hari), Z & service level, EOQ
    # sebelum pembulatan MOQ, S (biaya pesan/pesanan) & H (biaya simpan/unit/periode).
    # NULL = baris sebelum 23 Nov 2026. Rumus tetap hanya di reorder_service.
    mu_period: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    sigma_period: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    period_days: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    lead_time_days_used: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    z_value: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    service_level_pct_used: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    eoq_raw_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    ordering_cost_per_order: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    holding_cost_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
