"""
Peta izin RBAC — sumber tunggal role per aksi tulis (CR v3.5 §3, PRD FR-8.2).

Semua endpoint tulis memakai `Depends(require_permission("<action>"))`
(`app/api/deps.py`), bukan `require_role(...)` tersebar. Seluruh `GET` (termasuk
export & download template) terbuka untuk semua role terautentikasi.

Peta yang sama ada di `frontend/src/lib/permissions.ts` (menyembunyikan tombol tulis);
`tests/unit/test_rbac.py` memastikan keduanya tidak drift. Admin = superset PPIC.
"""

ADMIN_ONLY: tuple[str, ...] = ("admin",)
PLANNER: tuple[str, ...] = ("admin", "ppic")

PERMISSIONS: dict[str, tuple[str, ...]] = {
    "master.write": ADMIN_ONLY,  # produk, material, BOM, komponen, gudang, template biaya
    "settings.write": ADMIN_ONLY,  # Pengaturan Forecast
    "extvar.define": ADMIN_ONLY,  # definisi variabel eksternal + hapus nilai
    "extvar.import": PLANNER,  # import nilai bulanan (+ dry-run)
    "data.upload": PLANNER,  # upload demand
    "data.import_stock": PLANNER,  # stok ERP & pemakaian aktual
    "forecast.run": PLANNER,
    "forecast.select": PLANNER,  # pilih metode per produk / per run
    "override.create": PLANNER,
    "planning.run": PLANNER,  # reorder, plan, proyeksi stok
    "capacity.adjust": PLANNER,  # suggest / simpan / reset
}
