"""v3.0: forecast_results comparative selection columns

Additive (larangan #13 / strategi migrasi §0): tambah kolom metrik comparative
(mad/mfe/mse/mape), candidates_evaluated, dan perlebar method_used ke 30 char untuk
menampung nama metode v3.0 (moving_average/exponential_smoothing/random_forest/xgboost/lstm).
Kolom legacy `data_profile` DIBIARKAN (nullable) sampai cutover Fase 9.

Revision ID: a1b2c3d4e5f6
Revises: 6366f084a6d9
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "6366f084a6d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("forecast_results", sa.Column("candidates_evaluated", JSONB(), nullable=True))
    op.add_column("forecast_results", sa.Column("mad", sa.Numeric(18, 6), nullable=True))
    op.add_column("forecast_results", sa.Column("mfe", sa.Numeric(18, 6), nullable=True))
    op.add_column("forecast_results", sa.Column("mse", sa.Numeric(18, 6), nullable=True))
    op.add_column("forecast_results", sa.Column("mape", sa.Numeric(18, 6), nullable=True))
    op.alter_column(
        "forecast_results", "method_used", type_=sa.String(30), existing_type=sa.String(20), existing_nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "forecast_results", "method_used", type_=sa.String(20), existing_type=sa.String(30), existing_nullable=True
    )
    op.drop_column("forecast_results", "mape")
    op.drop_column("forecast_results", "mse")
    op.drop_column("forecast_results", "mfe")
    op.drop_column("forecast_results", "mad")
    op.drop_column("forecast_results", "candidates_evaluated")
