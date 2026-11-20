"""
Penanda OpenAPI bersama untuk router v1.

`INTERNAL_IMPORT` (CR v3.5 §5.1, keputusan user 20 Nov 2026): import CSV master data
(produk, material, BOM) **tidak punya UI** — dipakai untuk seed/migrasi data awal oleh
Admin lewat API. Ditandai tag `internal` + `x-internal: true` di OpenAPI supaya tidak
dianggap fitur yang terlupa di frontend. RBAC tetap `master.write`.
"""

INTERNAL_IMPORT: dict = {
    "tags": ["internal"],
    "openapi_extra": {"x-internal": True},
    "description": (
        "**Internal** — untuk seed/migrasi data master awal lewat API (tanpa UI, CR v3.5 §5.1). "
        "Input harian master data lewat form CRUD. Hanya Admin (`master.write`)."
    ),
}
