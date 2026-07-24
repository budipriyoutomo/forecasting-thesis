"""create upload_sessions and consumption_history tables

Revision ID: 9a85016d7be7
Revises: 6428318b5bb5
Create Date: 2026-07-24

Fase 3 — tabel `upload_sessions` & `consumption_history` (docs/ARCHITECTURE.md §4).
Lihat RECONCILIATION.md #14 untuk deviasi consumption_history (material_code +
material_id nullable).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9a85016d7be7"
down_revision: Union[str, None] = "6428318b5bb5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upload_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_size_kb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_materials_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("preview_data", postgresql.JSONB(), nullable=True),
        sa.Column("warnings", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_upload_sessions_user_id", "upload_sessions", ["user_id"])

    op.create_table(
        "consumption_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("material_code", sa.String(length=50), nullable=False),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id"),
            nullable=True,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "upload_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("upload_sessions.id"),
            nullable=False,
        ),
    )
    op.create_index("ix_consumption_history_material_code", "consumption_history", ["material_code"])
    op.create_index("ix_consumption_history_material_id", "consumption_history", ["material_id"])
    op.create_index(
        "ix_consumption_history_upload_session_id", "consumption_history", ["upload_session_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_consumption_history_upload_session_id", table_name="consumption_history")
    op.drop_index("ix_consumption_history_material_id", table_name="consumption_history")
    op.drop_index("ix_consumption_history_material_code", table_name="consumption_history")
    op.drop_table("consumption_history")
    op.drop_index("ix_upload_sessions_user_id", table_name="upload_sessions")
    op.drop_table("upload_sessions")
