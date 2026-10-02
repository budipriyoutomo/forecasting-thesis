import type { Bom } from "@/types/bom";
import type { Product } from "@/types/product";

export interface ProductBomCost {
  product_id: string;
  /** Σ line_cost baris BOM yang materialnya punya harga (Rp per unit produk). */
  material_cost: number;
  /** HPP produk, null bila belum diisi. */
  cost_price: number | null;
  /** HPP − biaya material; null bila HPP kosong. */
  margin_vs_hpp: number | null;
  /** Jumlah baris BOM yang materialnya belum punya harga — total jadi belum lengkap. */
  n_without_price: number;
}

// Ringkasan biaya material per unit produk dari baris BOM (Fase 10). Dihitung di
// klien dari `line_cost` backend — tidak dipersist, tidak menimpa HPP.
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
      const raw = productById.get(product_id)?.cost_price;
      const cost_price = raw == null ? null : Number(raw);
      return {
        product_id,
        material_cost: cost,
        cost_price,
        margin_vs_hpp: cost_price === null ? null : cost_price - cost,
        n_without_price: missing,
      };
    })
    .sort((a, b) =>
      (productById.get(a.product_id)?.code ?? a.product_id).localeCompare(
        productById.get(b.product_id)?.code ?? b.product_id,
      ),
    );
}
