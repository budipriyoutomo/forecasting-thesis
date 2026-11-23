"""v3.8: upload_sessions.file_url nullable — storage best-effort (23 Nov 2026)

Object storage belum dikonfigurasi (S3_* kosong, mis. dev lokal) dulu membuat semua endpoint
/uploads gagal STORAGE_UPLOAD_FAILED. Kini upload demand tetap tersimpan tanpa arsip file asli
→ file_url NULL + warning di upload session. Hanya melonggarkan constraint: baris lama tak berubah.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("upload_sessions", "file_url", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE upload_sessions SET file_url = '' WHERE file_url IS NULL")
    op.alter_column("upload_sessions", "file_url", existing_type=sa.Text(), nullable=False)
