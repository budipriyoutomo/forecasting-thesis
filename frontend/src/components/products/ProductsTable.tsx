"use client";

import type { Product } from "@/types/product";

export function ProductsTable({
  products,
  onEdit,
  onDelete,
}: {
  products: Product[];
  onEdit?: (p: Product) => void;
  onDelete?: (p: Product) => void;
}) {
  if (products.length === 0) {
    return <p className="text-sm text-muted-foreground">Belum ada produk.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-2 pr-4">Kode SKU</th>
            <th className="py-2 pr-4">Nama</th>
            <th className="py-2 pr-4">Kategori</th>
            <th className="py-2 pr-4">Satuan</th>
            <th className="py-2" />
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id} className="border-b">
              <td className="py-2 pr-4 font-medium">{p.code}</td>
              <td className="py-2 pr-4">{p.name}</td>
              <td className="py-2 pr-4">{p.category ?? "—"}</td>
              <td className="py-2 pr-4">{p.unit}</td>
              <td className="py-2 text-right">
                {onEdit && (
                  <button className="mr-3 text-primary hover:underline" onClick={() => onEdit(p)}>
                    Ubah
                  </button>
                )}
                {onDelete && (
                  <button className="text-destructive hover:underline" onClick={() => onDelete(p)}>
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
