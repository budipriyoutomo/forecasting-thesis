"""v3.0 cutover Fase 9: drop kolom legacy forecast_results (data_profile, material_id)

Cutover ke v3.0-only. `forecast_results` jalur v3.0 mengisi `product_id`; kolom
v2.0 `material_id` (FK materials) dan `data_profile` (kuadran ADI/CV² legacy)
sudah tidak ditulis/dibaca kode aktif (diverifikasi: tidak ada ForecastResult(...)
yang mengisinya, tidak ada query yang memfilternya). Reversible via downgrade.

Catatan: `consumption_history` TIDAK di-drop — jalur upload raw-material v2.0
sengaja dipertahankan (RECONCILIATION §Keputusan Terbuka v3.0 poin 1/2). Engine
legacy di `engines/legacy/` juga tetap (AGENTS.md larangan #16).

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_forecast_results_material_id", table_name="forecast_results")
    op.drop_column("forecast_results", "material_id")
    op.drop_column("forecast_results", "data_profile")


def downgrade() -> None:
    # Re-add sesuai state pra-cutover: material_id nullable (setelah e5f6a7b8c9d0),
    # data_profile JSONB nullable.
    op.add_column(
        "forecast_results",
        sa.Column("data_profile", JSONB(), nullable=True),
    )
    op.add_column(
        "forecast_results",
        sa.Column(
            "material_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materials.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_forecast_results_material_id", "forecast_results", ["material_id"])
