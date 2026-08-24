"""v3.0: drop material_requirements — forecast berhenti di level produk

DESTRUKTIF. Hasil forecast tidak lagi diturunkan ke BOM/material, jadi tabel
`material_requirements` dan override yang menargetkannya (`target_type =
'material_requirement'`) dibuang. Reorder & cost tetap memakai BOM lewat
breakdown deret di memori (tidak menyentuh tabel ini).

`downgrade()` membuat ulang struktur tabel, TAPI isinya tidak bisa dipulihkan.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM overrides WHERE target_type = 'material_requirement'")
    op.drop_index("ix_material_requirements_material_id", table_name="material_requirements")
    op.drop_index("ix_material_requirements_run_id", table_name="material_requirements")
    op.drop_table("material_requirements")


def downgrade() -> None:
    op.create_table(
        "material_requirements",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("forecast_runs.id"), nullable=False),
        sa.Column("material_id", UUID(as_uuid=True), sa.ForeignKey("materials.id"), nullable=False),
        sa.Column("forecast_qty", sa.Numeric(18, 4), nullable=False),
        sa.Column("standard_usage_qty", sa.Numeric(18, 4), nullable=True),
        sa.Column("actual_usage_qty", sa.Numeric(18, 4), nullable=True),
        sa.Column("buffer_stock_pct", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_material_requirements_run_id", "material_requirements", ["run_id"])
    op.create_index("ix_material_requirements_material_id", "material_requirements", ["material_id"])
