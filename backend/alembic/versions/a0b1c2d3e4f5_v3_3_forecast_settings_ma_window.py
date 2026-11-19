"""v3.3: window Moving Average di master data Pengaturan Forecast (19 Nov 2026)

`forecast_settings.ma_window` menggantikan env MOVING_AVERAGE_WINDOW supaya bisa diubah
dari UI tanpa redeploy (pola sama dengan es_alpha_grid / service_level_pct). Default 3 =
nilai env sebelumnya di seluruh contoh env repo; rentang 1..12 (CHECK).
Additive — baris singleton yang sudah ada mendapat 3.

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "forecast_settings", sa.Column("ma_window", sa.SmallInteger(), nullable=False, server_default="3")
    )
    op.create_check_constraint(
        "ck_forecast_settings_ma_window", "forecast_settings", "ma_window BETWEEN 1 AND 12"
    )


def downgrade() -> None:
    op.drop_constraint("ck_forecast_settings_ma_window", "forecast_settings", type_="check")
    op.drop_column("forecast_settings", "ma_window")
