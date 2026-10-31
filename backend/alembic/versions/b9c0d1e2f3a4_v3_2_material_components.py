"""v3.2 Fase 11.3: komponen material (BOM level 2+)

REVISI_V2 §3.4 / Keputusan #4: Preform ← Bottle, informasi saja (Bottle dibeli jadi).
Net-new. Siklus dicegah di service (BOM_CYCLE_DETECTED); CHECK mencegah self-loop.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "material_components",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_material_id", _UUID, sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_material_id", _UUID, sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qty_per_unit", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("parent_material_id", "component_material_id", name="uq_material_components_pair"),
        sa.CheckConstraint("parent_material_id <> component_material_id", name="ck_material_components_not_self"),
        sa.CheckConstraint("qty_per_unit > 0", name="ck_material_components_qty_positive"),
    )
    op.create_index("ix_material_components_parent_material_id", "material_components", ["parent_material_id"])


def downgrade() -> None:
    op.drop_index("ix_material_components_parent_material_id", table_name="material_components")
    op.drop_table("material_components")
