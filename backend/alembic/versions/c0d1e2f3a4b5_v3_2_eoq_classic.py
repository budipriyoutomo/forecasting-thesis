"""v3.2 Fase 11.4: EOQ klasik thesis + perencanaan di master data

REVISI_V2 §3.5 / Keputusan #5:
- cost_templates.holding_cost_rate_pct (i % tahunan); cost_template_items.period_basis
  (monthly | annual) + item_type MAINTENANCE.
- reorder_recommendations: eoq_method, item_status, annual_demand, unit_price_used,
  holding_rate_used.
- forecast_settings: service_level_pct & eoq_method (menggantikan env SERVICE_LEVEL_PCT /
  rencana EOQ_METHOD — permintaan user, setting bukan di env).
Additive; data lama: period_basis 'monthly', eoq_method/item_status NULL.

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, None] = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cost_templates", sa.Column("holding_cost_rate_pct", sa.Numeric(9, 4), nullable=True))
    op.create_check_constraint(
        "ck_cost_templates_holding_rate",
        "cost_templates",
        "holding_cost_rate_pct IS NULL OR (holding_cost_rate_pct > 0 AND holding_cost_rate_pct <= 100)",
    )
    op.add_column(
        "cost_template_items", sa.Column("period_basis", sa.String(10), nullable=False, server_default="monthly")
    )
    op.drop_constraint("ck_cost_template_items_type", "cost_template_items", type_="check")
    op.create_check_constraint(
        "ck_cost_template_items_type", "cost_template_items", "item_type IN ('OVERHEAD', 'STORAGE_ASSET', 'MAINTENANCE')"
    )
    op.create_check_constraint(
        "ck_cost_template_items_period_basis", "cost_template_items", "period_basis IN ('monthly', 'annual')"
    )

    for name, type_ in (
        ("eoq_method", sa.String(10)),
        ("item_status", sa.String(30)),
        ("annual_demand", sa.Numeric(18, 4)),
        ("unit_price_used", sa.Numeric(18, 4)),
        ("holding_rate_used", sa.Numeric(9, 4)),
    ):
        op.add_column("reorder_recommendations", sa.Column(name, type_, nullable=True))

    op.add_column(
        "forecast_settings", sa.Column("service_level_pct", sa.Float(), nullable=False, server_default="95")
    )
    op.add_column("forecast_settings", sa.Column("eoq_method", sa.String(10), nullable=False, server_default="classic"))
    op.create_check_constraint(
        "ck_forecast_settings_service_level", "forecast_settings", "service_level_pct > 50 AND service_level_pct < 100"
    )
    op.create_check_constraint(
        "ck_forecast_settings_eoq_method", "forecast_settings", "eoq_method IN ('classic', 'dynamic')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_forecast_settings_eoq_method", "forecast_settings", type_="check")
    op.drop_constraint("ck_forecast_settings_service_level", "forecast_settings", type_="check")
    op.drop_column("forecast_settings", "eoq_method")
    op.drop_column("forecast_settings", "service_level_pct")
    for name in ("holding_rate_used", "unit_price_used", "annual_demand", "item_status", "eoq_method"):
        op.drop_column("reorder_recommendations", name)
    op.drop_constraint("ck_cost_template_items_period_basis", "cost_template_items", type_="check")
    op.drop_constraint("ck_cost_template_items_type", "cost_template_items", type_="check")
    op.execute("DELETE FROM cost_template_items WHERE item_type = 'MAINTENANCE'")
    op.create_check_constraint(
        "ck_cost_template_items_type", "cost_template_items", "item_type IN ('OVERHEAD', 'STORAGE_ASSET')"
    )
    op.drop_column("cost_template_items", "period_basis")
    op.drop_constraint("ck_cost_templates_holding_rate", "cost_templates", type_="check")
    op.drop_column("cost_templates", "holding_cost_rate_pct")
