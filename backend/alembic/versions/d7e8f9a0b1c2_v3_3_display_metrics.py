"""v3.3 Fase 11.15: tanpa metode pemenang — metrik tampil (checkbox) di Pengaturan Forecast

Mode otomatis tidak lagi memilih pemenang (RECONCILIATION §"Fase 11.15"); planner memilih
metode per produk lewat override append-only. `forecast_settings.ranking_metric` (metrik
penentu pemenang) tidak bermakna lagi → diganti `display_metrics` (metrik yang DITAMPILKAN di
hasil forecast; NULL = semua). `forecast_runs.ranking_metric` TIDAK disentuh — riwayat run lama.

Downgrade mengembalikan `ranking_metric` ke default `mad` (nilai sebelum upgrade tidak disimpan).

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, None] = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "forecast_settings",
        sa.Column("display_metrics", postgresql.ARRAY(sa.String(10)), nullable=True),
    )
    op.drop_constraint("ck_forecast_settings_ranking_metric", "forecast_settings", type_="check")
    op.drop_column("forecast_settings", "ranking_metric")


def downgrade() -> None:
    op.add_column(
        "forecast_settings",
        sa.Column("ranking_metric", sa.String(10), nullable=False, server_default="mad"),
    )
    op.create_check_constraint(
        "ck_forecast_settings_ranking_metric",
        "forecast_settings",
        "ranking_metric IN ('mad', 'mfe_abs', 'mape')",
    )
    op.drop_column("forecast_settings", "display_metrics")
