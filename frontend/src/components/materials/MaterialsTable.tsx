"use client";

import type { Material } from "@/types/material";

export function MaterialsTable({
  materials,
  onEdit,
  onDelete,
}: {
  materials: Material[];
  onEdit?: (m: Material) => void;
  onDelete?: (m: Material) => void;
}) {
  if (materials.length === 0) {
    return <p className="text-sm text-muted-foreground">Belum ada material.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-2 pr-4">Kode</th>
            <th className="py-2 pr-4">Nama</th>
            <th className="py-2 pr-4">Satuan</th>
            <th className="py-2 pr-4">Lead time</th>
            <th className="py-2 pr-4">MOQ</th>
            <th className="py-2" />
          </tr>
        </thead>
        <tbody>
          {materials.map((m) => (
            <tr key={m.id} className="border-b">
              <td className="py-2 pr-4 font-medium">{m.code}</td>
              <td className="py-2 pr-4">{m.name}</td>
              <td className="py-2 pr-4">{m.unit}</td>
              <td className="py-2 pr-4">{m.lead_time_days} hari</td>
              <td className="py-2 pr-4">{m.moq}</td>
              <td className="py-2 text-right">
                {onEdit && (
                  <button className="mr-3 text-primary hover:underline" onClick={() => onEdit(m)}>
                    Ubah
                  </button>
                )}
                {onDelete && (
                  <button className="text-destructive hover:underline" onClick={() => onDelete(m)}>
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
