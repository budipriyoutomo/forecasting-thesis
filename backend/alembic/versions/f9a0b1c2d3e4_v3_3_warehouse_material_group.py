"""v3.3: kapasitas gudang per GRUP MATERIAL (19 Nov 2026)

Thesis "Pengumpulan Data" mencatat kapasitas gudang per material group (mis. 6 warna Cap
berbagi 171 pallet). Target `material` (per item, Fase 11.6) diganti `material_group`:
  - warehouse_config.item_type melebar ke String(20), + kolom material_group.
  - Config per material yang ada dikonversi ke grup = materials.category material itu.
    Material tanpa category diberi category = kode material (supaya grupnya terbentuk);
    bila dua material satu grup sudah punya config, yang pertama (created_at) dipakai,
    sisanya dihapus — kapasitas grup tidak bisa dijumlahkan secara aman.
  - CHECK target & partial unique index (lower(material_group)) diperbarui.
Kolom material_id dipertahankan (tidak diisi lagi) supaya downgrade bisa memulihkan.

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, None] = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("warehouse_config", "item_type", type_=sa.String(20), existing_nullable=False)
    op.add_column("warehouse_config", sa.Column("material_group", sa.String(100), nullable=True))
    op.drop_constraint("ck_warehouse_config_target", "warehouse_config", type_="check")

    # Data: material tanpa grup yang punya config → grup = kode material.
    op.execute(
        """
        UPDATE materials m SET category = m.code
        FROM warehouse_config w
        WHERE w.item_type = 'material' AND w.material_id = m.id
          AND (m.category IS NULL OR btrim(m.category) = '')
        """
    )
    # Satu config per grup: simpan yang paling awal, hapus duplikat grup.
    op.execute(
        """
        DELETE FROM warehouse_config w USING (
            SELECT w2.id, row_number() OVER (
                PARTITION BY lower(btrim(m.category)) ORDER BY w2.created_at, w2.id
            ) AS rn
            FROM warehouse_config w2 JOIN materials m ON m.id = w2.material_id
            WHERE w2.item_type = 'material'
        ) d
        WHERE w.id = d.id AND d.rn > 1
        """
    )
    op.execute(
        """
        UPDATE warehouse_config w
        SET item_type = 'material_group', material_group = btrim(m.category), material_id = NULL
        FROM materials m
        WHERE w.item_type = 'material' AND w.material_id = m.id
        """
    )

    op.drop_index("uq_warehouse_config_material", table_name="warehouse_config")
    op.create_index(
        "uq_warehouse_config_material_group", "warehouse_config", [sa.text("lower(material_group)")],
        unique=True, postgresql_where=sa.text("item_type = 'material_group'"),
    )
    op.create_check_constraint(
        "ck_warehouse_config_target",
        "warehouse_config",
        "(item_type = 'product' AND product_id IS NOT NULL AND material_id IS NULL AND material_group IS NULL) OR "
        "(item_type = 'material_group' AND material_group IS NOT NULL AND product_id IS NULL AND material_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_warehouse_config_target", "warehouse_config", type_="check")
    op.drop_index("uq_warehouse_config_material_group", table_name="warehouse_config")
    # Grup → material pertama (kode terkecil) di grup itu; grup tanpa material dihapus.
    op.execute(
        """
        UPDATE warehouse_config w SET item_type = 'material', material_id = (
            SELECT m.id FROM materials m
            WHERE lower(btrim(m.category)) = lower(w.material_group)
            ORDER BY m.code LIMIT 1
        )
        WHERE w.item_type = 'material_group'
        """
    )
    op.execute("DELETE FROM warehouse_config WHERE item_type = 'material' AND material_id IS NULL")
    op.create_index(
        "uq_warehouse_config_material", "warehouse_config", ["material_id"],
        unique=True, postgresql_where=sa.text("item_type = 'material'"),
    )
    op.create_check_constraint(
        "ck_warehouse_config_target",
        "warehouse_config",
        "(item_type = 'product' AND product_id IS NOT NULL AND material_id IS NULL) OR "
        "(item_type = 'material' AND material_id IS NOT NULL AND product_id IS NULL)",
    )
    op.drop_column("warehouse_config", "material_group")
    op.alter_column("warehouse_config", "item_type", type_=sa.String(10), existing_nullable=False)
