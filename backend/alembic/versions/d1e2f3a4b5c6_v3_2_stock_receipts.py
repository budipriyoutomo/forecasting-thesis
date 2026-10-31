"""v3.2 Fase 11.5: stok ERP (stock_snapshots) & estimasi kedatangan (material_receipts)

REVISI_V2 §3.3. Net-new + reorder_recommendations.current_stock_used/stock_source
(revisi keputusan #16: snapshot ERP menang, `current_stock` request = fallback).

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "stock_snapshots",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("material_id", _UUID, sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("material_id", "snapshot_date", name="uq_stock_snapshots_material_date"),
        sa.CheckConstraint("qty >= 0", name="ck_stock_snapshots_qty"),
    )
    op.create_index("ix_stock_snapshots_material_id", "stock_snapshots", ["material_id"])
    op.create_table(
        "material_receipts",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("material_id", _UUID, sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expected_date", sa.Date(), nullable=False),
        sa.Column("qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("source", sa.String(10), nullable=False, server_default="manual"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", _UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("qty > 0", name="ck_material_receipts_qty"),
        sa.CheckConstraint("source IN ('manual', 'upload')", name="ck_material_receipts_source"),
    )
    op.create_index("ix_material_receipts_material_id", "material_receipts", ["material_id"])
    op.add_column("reorder_recommendations", sa.Column("current_stock_used", sa.Numeric(18, 4), nullable=True))
    op.add_column("reorder_recommendations", sa.Column("stock_source", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("reorder_recommendations", "stock_source")
    op.drop_column("reorder_recommendations", "current_stock_used")
    op.drop_index("ix_material_receipts_material_id", table_name="material_receipts")
    op.drop_table("material_receipts")
    op.drop_index("ix_stock_snapshots_material_id", table_name="stock_snapshots")
    op.drop_table("stock_snapshots")
