"""v3.3 Fase 11.14: konteks override (run_id, material_id)

Rekomendasi reorder di-generate ulang dengan id baru (replace_for_run), sehingga override
yang hanya menyimpan target_id kehilangan targetnya di UI. Kolom konteks membuat riwayat
& qty override yang berlaku dicari per (run, material). Additive; backfill baris lama yang
targetnya masih ada.

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, None] = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("overrides", sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("overrides", sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_overrides_run_id", "overrides", ["run_id"])
    op.create_index("ix_overrides_material_id", "overrides", ["material_id"])
    op.execute(
        "UPDATE overrides o SET run_id = r.run_id, material_id = r.material_id "
        "FROM reorder_recommendations r "
        "WHERE o.target_type = 'reorder_recommendation' AND o.target_id = r.id"
    )
    op.execute(
        "UPDATE overrides o SET run_id = f.run_id FROM forecast_results f "
        "WHERE o.target_type = 'forecast_result' AND o.target_id = f.id"
    )


def downgrade() -> None:
    op.drop_index("ix_overrides_material_id", table_name="overrides")
    op.drop_index("ix_overrides_run_id", table_name="overrides")
    op.drop_column("overrides", "material_id")
    op.drop_column("overrides", "run_id")
