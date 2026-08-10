"""v3.0 cutover lanjutan: drop tabel legacy consumption_history

Membalik catatan di `b8c9d0e1f2a3` ("consumption_history TIDAK di-drop — jalur
upload raw-material v2.0 sengaja dipertahankan"). Audit 4 Agustus 2026 menunjukkan
jalur itu **sudah mati sepenuhnya**, bukan sekadar jarang dipakai:

  - `data_ingestion_service.REQUIRED_COLUMNS` = {product_code, period, actual} →
    upload berformat `material_code` ditolak, jadi tabel ini tak bisa terisi.
  - `UploadService` menulis `demand_history`, tidak pernah `consumption_history`.
  - `SqlConsumptionHistoryRepository.list_for_material` nol pemanggil (tak pernah dibaca).
  - `ReorderService` mengambil μ/σ dari breakdown BOM atas forecast produk.

Keputusan user 4 Agustus 2026: drop, dan lepas rencana forecasting raw material
langsung (RECONCILIATION §Keputusan Terbuka v3.0 poin 1). Engine legacy di
`engines/legacy/` TETAP tidak dihapus (AGENTS.md larangan #16) — itu keputusan
terpisah dan masih berlaku.

Reversible: `downgrade()` membuat ulang tabel + indeks persis seperti definisi
`9a85016d7be7`. Yang TIDAK kembali adalah isi barisnya — drop tabel menghapus
data secara permanen. Backup dulu bila instance produksi masih menyimpan histori
raw material v2.0 yang bernilai.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_consumption_history_upload_session_id", table_name="consumption_history")
    op.drop_index("ix_consumption_history_material_id", table_name="consumption_history")
    op.drop_index("ix_consumption_history_material_code", table_name="consumption_history")
    op.drop_table("consumption_history")


def downgrade() -> None:
    # Definisi identik dengan 9a85016d7be7 (material_id nullable — RECONCILIATION #14).
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
