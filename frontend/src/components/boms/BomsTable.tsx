"use client";

import type { Bom } from "@/types/bom";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";

export function BomsTable({
  boms,
  products,
  materials,
  onEdit,
  onDelete,
}: {
  boms: Bom[];
  products: Product[];
  materials: Material[];
  onEdit?: (b: Bom) => void;
  onDelete?: (b: Bom) => void;
}) {
  if (boms.length === 0) {
    return <p className="text-sm text-muted-foreground">Belum ada baris BOM.</p>;
  }

  const productLabel = (id: string) => {
    const p = products.find((x) => x.id === id);
    return p ? p.code : id;
  };
  const materialLabel = (id: string) => {
    const m = materials.find((x) => x.id === id);
    return m ? m.code : id;
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-2 pr-4">Produk</th>
            <th className="py-2 pr-4">Material</th>
            <th className="py-2 pr-4">Qty / unit</th>
            <th className="py-2" />
          </tr>
        </thead>
        <tbody>
          {boms.map((b) => (
            <tr key={b.id} className="border-b">
              <td className="py-2 pr-4 font-medium">{productLabel(b.product_id)}</td>
              <td className="py-2 pr-4">{materialLabel(b.material_id)}</td>
              <td className="py-2 pr-4">{b.qty_per_unit}</td>
              <td className="py-2 text-right">
                {onEdit && (
                  <button className="mr-3 text-primary hover:underline" onClick={() => onEdit(b)}>
                    Ubah
                  </button>
                )}
                {onDelete && (
                  <button className="text-destructive hover:underline" onClick={() => onDelete(b)}>
                    Hapus
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
