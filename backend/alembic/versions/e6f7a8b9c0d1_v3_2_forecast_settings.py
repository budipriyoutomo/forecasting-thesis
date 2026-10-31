"""v3.2 Fase 11.2: master data Pengaturan Forecast + ranking/FI/hyperparameter hasil forecast

forecast_settings: metrik ranking, metode aktif, opsi engine (grid α ES, metrik α, grid
search ML, cap outlier). forecast_runs.ranking_metric (snapshot). forecast_results:
feature_importance & hyperparameters (JSONB).

Metrik ranking pemenang & daftar metode aktif Comparative Selection pindah dari env
(FORECAST_RANKING_METRIC, FORECAST_ENGINES_ENABLED) ke master data (Keputusan #6,
docs/REVISI_V2.md §6.1). `enabled_methods` NULL → seluruh metode terdaftar. `forecast_settings` = satu
baris global (CHECK id = 1); tanpa baris → default `mad` di kode. Additive, tanpa
backfill: run lama `ranking_metric` NULL.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_settings",
        sa.Column("id", sa.SmallInteger(), primary_key=True, server_default="1"),
        sa.Column("ranking_metric", sa.String(10), nullable=False, server_default="mad"),
        sa.Column("enabled_methods", postgresql.ARRAY(sa.String(50)), nullable=True),
        sa.Column("es_alpha_grid", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("es_alpha_metric", sa.String(10), nullable=False, server_default="mad"),
        sa.Column("ml_grid_search", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ml_winsorize", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_forecast_settings_singleton"),
        sa.CheckConstraint(
            "ranking_metric IN ('mad', 'mfe_abs', 'mape')", name="ck_forecast_settings_ranking_metric"
        ),
        sa.CheckConstraint(
            "enabled_methods IS NULL OR cardinality(enabled_methods) > 0",
            name="ck_forecast_settings_enabled_methods_not_empty",
        ),
        sa.CheckConstraint(
            "es_alpha_grid IS NULL OR cardinality(es_alpha_grid) > 0",
            name="ck_forecast_settings_alpha_grid_not_empty",
        ),
        sa.CheckConstraint("es_alpha_metric IN ('mad', 'mape')", name="ck_forecast_settings_alpha_metric"),
    )
    op.add_column("forecast_runs", sa.Column("ranking_metric", sa.String(10), nullable=True))
    op.add_column("forecast_results", sa.Column("feature_importance", postgresql.JSONB(), nullable=True))
    op.add_column("forecast_results", sa.Column("hyperparameters", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("forecast_results", "hyperparameters")
    op.drop_column("forecast_results", "feature_importance")
    op.drop_column("forecast_runs", "ranking_metric")
    op.drop_table("forecast_settings")
