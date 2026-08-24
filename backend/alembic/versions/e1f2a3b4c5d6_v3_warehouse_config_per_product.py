"""v3.0: kapasitas gudang per produk (free input) + drop materials.qty_per_pallet

DESTRUKTIF. `warehouse_config` diganti dari "1 baris global per kategori (luas
gudang × dimensi palet)" jadi "1 baris per produk, capacity_qty bebas". Isi lama
tidak bisa dipetakan otomatis ke produk (tidak ada pemetaan kategori→produk),
jadi tabel di-drop & dibuat ulang kosong — planner isi ulang dari halaman
Warehouse. `warehouse_validations` ikut diganti (agregat pallet → per-produk
JSONB `details`); baris lama tidak relevan lagi.

`materials.qty_per_pallet` dihapus — tidak dipakai lagi setelah validasi
kapasitas tidak lagi berbasis palet (keputusan user 24 Agustus 2026).

`downgrade()` membuat ulang struktur tabel/kolom lama, TAPI isinya tidak bisa
dipulihkan.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_warehouse_validations_run_id", table_name="warehouse_validations")
    op.drop_table("warehouse_validations")
    op.drop_constraint("uq_warehouse_config_category", "warehouse_config", type_="unique")
    op.drop_table("warehouse_config")

    op.create_table(
        "warehouse_config",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("capacity_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_warehouse_config_product_id", "warehouse_config", ["product_id"])
    op.create_index("ix_warehouse_config_product_id", "warehouse_config", ["product_id"])

    op.create_table(
        "warehouse_validations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("is_within_capacity", sa.Boolean(), nullable=False),
        sa.Column("details", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_warehouse_validations_run_id", "warehouse_validations", ["run_id"])

    op.drop_column("materials", "qty_per_pallet")


def downgrade() -> None:
    op.add_column("materials", sa.Column("qty_per_pallet", sa.Numeric(18, 4), nullable=True))

    op.drop_index("ix_warehouse_validations_run_id", table_name="warehouse_validations")
    op.drop_table("warehouse_validations")
    op.drop_index("ix_warehouse_config_product_id", table_name="warehouse_config")
    op.drop_constraint("uq_warehouse_config_product_id", "warehouse_config", type_="unique")
    op.drop_table("warehouse_config")

    op.create_table(
        "warehouse_config",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("warehouse_area_m2", sa.Numeric(18, 4), nullable=False),
        sa.Column("pallet_dimension", JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_warehouse_config_category", "warehouse_config", ["category"])

    op.create_table(
        "warehouse_validations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("total_pallet_capacity", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_pallet_required", sa.Numeric(18, 4), nullable=False),
        sa.Column("is_within_capacity", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_warehouse_validations_run_id", "warehouse_validations", ["run_id"])
