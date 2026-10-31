"""
MaterialComponentService (Fase 11.3, 30 Oktober 2026) — BOM multi-level, REVISI_V2 §3.4.

Level 0 FG → level 1 material (tabel `boms`) → level 2+ komponen (`material_components`).
Keputusan #4: material level 1 dibeli (masuk EOQ/kapasitas); komponen level ≥ 2 hanya
informasi (`purchased = False`) — breakdown kebutuhan tetap single-level.
Siklus (A → … → A) ditolak: BOM_CYCLE_DETECTED (422).
"""
from collections.abc import Callable
from decimal import Decimal

from app.models.material_component import MaterialComponent
from app.utils.exceptions import (
    BomCycleDetectedError,
    MaterialComponentNotFoundError,
    MaterialNotFoundError,
    ProductNotFoundError,
)


def would_create_cycle(edges: dict[str, set[str]], parent: str, child: str) -> bool:
    """True bila menambah sisi parent → child membuat siklus (child sudah menjangkau parent)."""
    if parent == child:
        return True
    stack, seen = [child], set()
    while stack:
        node = stack.pop()
        if node == parent:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(edges.get(node, ()))
    return False


def _node(material, qty, level: int, component_id=None) -> dict:
    return {
        "material_id": str(material.id) if material else None,
        "code": getattr(material, "code", None),
        "name": getattr(material, "name", None),
        "unit": getattr(material, "unit", None),
        "qty_per_unit": float(qty),
        "level": level,
        "purchased": level == 1,
        "component_id": str(component_id) if component_id else None,
        "children": [],
    }


def build_bom_tree(product, bom_lines, materials_by_id: dict, components_by_parent: dict) -> dict:
    """Tree FG → material → komponen. `visited` menjaga data kotor (siklus) tidak loop."""

    def expand(node: dict, material_id: str, level: int, visited: frozenset) -> None:
        for comp in components_by_parent.get(material_id, []):
            cid = str(comp.component_material_id)
            if cid in visited:
                continue
            child = _node(materials_by_id.get(cid), comp.qty_per_unit, level, comp.id)
            expand(child, cid, level + 1, visited | {cid})
            node["children"].append(child)

    root = {
        "product_id": str(product.id),
        "code": product.code,
        "name": product.name,
        "level": 0,
        "children": [],
    }
    for line in bom_lines:
        mid = str(line.material_id)
        node = _node(materials_by_id.get(mid), line.qty_per_unit, 1)
        expand(node, mid, 2, frozenset({mid}))
        root["children"].append(node)
    return root


class MaterialComponentService:
    def __init__(self, repo, materials, products, boms, factory: Callable[..., object] = MaterialComponent):
        self._repo = repo
        self._materials = materials
        self._products = products
        self._boms = boms
        self._factory = factory

    async def list(self, parent_id: str):
        return await self._repo.list(parent_id)

    async def add(self, parent_id: str, component_id: str, qty_per_unit) -> object:
        for mid in (parent_id, component_id):
            if await self._materials.get_by_id(mid) is None:
                raise MaterialNotFoundError(f"Material '{mid}' tidak ditemukan.")
        edges: dict[str, set[str]] = {}
        for r in await self._repo.list():
            edges.setdefault(str(r.parent_material_id), set()).add(str(r.component_material_id))
        if would_create_cycle(edges, str(parent_id), str(component_id)):
            raise BomCycleDetectedError("Komponen ini membentuk siklus BOM (material menjadi komponen dirinya sendiri).")
        row = self._factory(
            parent_material_id=parent_id, component_material_id=component_id, qty_per_unit=Decimal(str(qty_per_unit))
        )
        return await self._repo.add(row)

    async def delete(self, component_row_id: str) -> None:
        row = await self._repo.get_by_id(component_row_id)
        if row is None:
            raise MaterialComponentNotFoundError("Komponen material tidak ditemukan.")
        await self._repo.delete(row)

    async def tree(self, product_id: str) -> dict:
        product = await self._products.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(f"Produk '{product_id}' tidak ditemukan.")
        materials = {str(m.id): m for m in await self._materials.list()}
        components: dict[str, list] = {}
        for r in await self._repo.list():
            components.setdefault(str(r.parent_material_id), []).append(r)
        return build_bom_tree(product, await self._boms.list(str(product_id)), materials, components)
