import type { Bom, MaterialComponent } from "@/types/bom";
import type { Product } from "@/types/product";

export interface ProductBomCost {
  product_id: string;
  /** Σ line_cost baris BOM yang materialnya punya harga (Rp per unit produk). */
  material_cost: number;
  /** Harga produk (`selling_price`), null bila belum diisi. */
  product_price: number | null;
  /** Harga produk − biaya material; null bila harga produk kosong. */
  margin: number | null;
  /** Jumlah baris BOM yang materialnya belum punya harga — total jadi belum lengkap. */
  n_without_price: number;
}

// Ringkasan biaya material per unit produk dari baris BOM (Fase 10). Dihitung di
// klien dari `line_cost` backend — tidak dipersist, tidak menimpa harga produk.
export function summarizeBomCosts(boms: Bom[], products: Product[]): ProductBomCost[] {
  const byProduct = new Map<string, { cost: number; missing: number }>();
  for (const b of boms) {
    const acc = byProduct.get(b.product_id) ?? { cost: 0, missing: 0 };
    if (b.line_cost == null) acc.missing += 1;
    else acc.cost += Number(b.line_cost);
    byProduct.set(b.product_id, acc);
  }

  const productById = new Map(products.map((p) => [p.id, p]));
  return [...byProduct.entries()]
    .map(([product_id, { cost, missing }]) => {
      const raw = productById.get(product_id)?.selling_price;
      const product_price = raw == null ? null : Number(raw);
      return {
        product_id,
        material_cost: cost,
        product_price,
        margin: product_price === null ? null : product_price - cost,
        n_without_price: missing,
      };
    })
    .sort((a, b) =>
      (productById.get(a.product_id)?.code ?? a.product_id).localeCompare(
        productById.get(b.product_id)?.code ?? b.product_id,
      ),
    );
}

export interface BomLevelRow {
  key: string;
  level: number;
  product_id: string;
  /** Material induk (null untuk level 1 — induknya produk). */
  parent_material_id: string | null;
  material_id: string;
  qty_per_unit: number;
  /** Baris `boms` asli (hanya level 1) — untuk ubah/hapus. */
  bom?: Bom;
  /** Id baris `material_components` (level 2+). */
  component_id?: string;
}

// Ratakan BOM multi-level ke baris tabel (19 Nov 2026): level 1 = baris `boms`,
// level 2+ = komponen material induknya, diletakkan tepat di bawah induk.
// `visited` per cabang menjaga data siklus tidak loop (backend juga menolak siklus).
export function flattenBomLevels(boms: Bom[], components: MaterialComponent[]): BomLevelRow[] {
  const byParent = new Map<string, MaterialComponent[]>();
  for (const c of components) byParent.set(c.parent_material_id, [...(byParent.get(c.parent_material_id) ?? []), c]);

  const rows: BomLevelRow[] = [];
  const expand = (b: Bom, parent: string, level: number, visited: Set<string>, path: string) => {
    for (const c of byParent.get(parent) ?? []) {
      if (visited.has(c.component_material_id)) continue;
      const key = `${path}/${c.id}`;
      rows.push({
        key,
        level,
        product_id: b.product_id,
        parent_material_id: parent,
        material_id: c.component_material_id,
        qty_per_unit: Number(c.qty_per_unit),
        component_id: c.id,
      });
      expand(b, c.component_material_id, level + 1, new Set([...visited, c.component_material_id]), key);
    }
  };
  for (const b of boms) {
    rows.push({
      key: b.id,
      level: b.level ?? 1,
      product_id: b.product_id,
      parent_material_id: null,
      material_id: b.material_id,
      qty_per_unit: Number(b.qty_per_unit),
      bom: b,
    });
    expand(b, b.material_id, 2, new Set([b.material_id]), b.id);
  }
  return rows;
}
