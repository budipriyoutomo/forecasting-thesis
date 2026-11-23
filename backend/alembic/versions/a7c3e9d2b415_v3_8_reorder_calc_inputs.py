"""reorder_recommendations: input perhitungan SS/ROP/EOQ (23 Nov 2026)

Menyimpan input yang dipakai reorder_service (μ/σ kebutuhan per periode, hari per periode,
lead time, Z & service level, EOQ sebelum pembulatan MOQ, S & H) supaya bagian
"Perencanaan persediaan" bisa menampilkan perhitungannya. Semua NULLABLE — baris lama
tetap valid (tampil "—" sampai perencanaan dijalankan ulang). Additive.

Revision ID: a7c3e9d2b415
Revises: e4f5a6b7c8d9
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3e9d2b415"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None

COLUMNS = (
    ("mu_period", sa.Numeric(18, 4)),
    ("sigma_period", sa.Numeric(18, 4)),
    ("period_days", sa.Numeric(9, 4)),
    ("lead_time_days_used", sa.Numeric(9, 4)),
    ("z_value", sa.Numeric(9, 4)),
    ("service_level_pct_used", sa.Numeric(6, 3)),
    ("eoq_raw_qty", sa.Numeric(18, 4)),
    ("ordering_cost_per_order", sa.Numeric(18, 4)),
    ("holding_cost_per_unit", sa.Numeric(18, 4)),
)


def upgrade() -> None:
    for name, type_ in COLUMNS:
        op.add_column("reorder_recommendations", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(COLUMNS):
        op.drop_column("reorder_recommendations", name)
