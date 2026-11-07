"""v3.3 Fase 11.9: rumus ROP & kebijakan qty pesan configurable (sumber tunggal)

Tabel Reorder dan Proyeksi Stok sebelumnya memakai titik pesan & qty pesan berbeda
(ROP = μ·L + SS + B vs SS + B; max(MOQ, S − stok) vs n × EOQ). Sekarang keduanya dari
`reorder_service` dan diatur di Pengaturan Forecast:

- forecast_settings.rop_formula       standard | with_buffer (default)
- forecast_settings.order_qty_policy  eoq | order_up_to (default)
- reorder_recommendations: rop_formula_used, order_qty_policy_used (audit),
  order_up_to_level, moq_used (input Proyeksi Stok).

Additive. Default = perilaku Reorder sebelum v3.3; baris lama kolom baru NULL
(Proyeksi Stok fallback order_up_to, S = 2·ROP − SS − B).

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "forecast_settings", sa.Column("rop_formula", sa.String(20), nullable=False, server_default="with_buffer")
    )
    op.add_column(
        "forecast_settings",
        sa.Column("order_qty_policy", sa.String(20), nullable=False, server_default="order_up_to"),
    )
    op.create_check_constraint(
        "ck_forecast_settings_rop_formula", "forecast_settings", "rop_formula IN ('standard', 'with_buffer')"
    )
    op.create_check_constraint(
        "ck_forecast_settings_order_qty_policy", "forecast_settings", "order_qty_policy IN ('eoq', 'order_up_to')"
    )
    op.add_column("reorder_recommendations", sa.Column("rop_formula_used", sa.String(20), nullable=True))
    op.add_column("reorder_recommendations", sa.Column("order_qty_policy_used", sa.String(20), nullable=True))
    op.add_column("reorder_recommendations", sa.Column("order_up_to_level", sa.Numeric(18, 4), nullable=True))
    op.add_column("reorder_recommendations", sa.Column("moq_used", sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    for name in ("moq_used", "order_up_to_level", "order_qty_policy_used", "rop_formula_used"):
        op.drop_column("reorder_recommendations", name)
    op.drop_constraint("ck_forecast_settings_order_qty_policy", "forecast_settings", type_="check")
    op.drop_constraint("ck_forecast_settings_rop_formula", "forecast_settings", type_="check")
    op.drop_column("forecast_settings", "order_qty_policy")
    op.drop_column("forecast_settings", "rop_formula")
