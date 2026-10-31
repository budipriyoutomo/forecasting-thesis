"use client";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatNumber } from "@/lib/format";
import type { LatestStock } from "@/types/inventory";
import type { Material } from "@/types/material";

// Stok awal proyeksi = snapshot ERP terakhir per material (Fase 11.5).
export function LatestStockTable({ latest, materials }: { latest: LatestStock[]; materials: Material[] }) {
  const byId = new Map(latest.map((l) => [l.material_id, l]));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Material</TableHead>
            <TableHead>Stok</TableHead>
            <TableHead>Tanggal snapshot</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {materials.map((m) => {
            const s = byId.get(m.id);
            return (
              <TableRow key={m.id}>
                <TableCell>
                  <span className="font-medium">{m.code}</span>
                  <span className="block text-xs text-muted-foreground">{m.name}</span>
                </TableCell>
                <TableCell className="tabular-nums">{s ? `${formatNumber(s.qty)}` : "—"}</TableCell>
                <TableCell>
                  {s ? formatDate(s.snapshot_date) : <span className="text-muted-foreground">Belum ada snapshot</span>}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
