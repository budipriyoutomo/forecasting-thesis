"use client";

import { EmptyState } from "@/components/common/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { WasteFactor } from "@/types/inventory";
import type { Material } from "@/types/material";

// Buffer stock thesis = aktual : standar pemakaian (Fase 11.1, Keputusan #8):
// buffer = max(0, faktor − 1) × kebutuhan periode.
export function WasteFactorTable({ factors, materials }: { factors: WasteFactor[]; materials: Material[] }) {
  if (factors.length === 0) return <EmptyState message="Belum ada data pemakaian aktual material." />;
  const code = new Map(materials.map((m) => [m.id, m.code]));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Material</TableHead>
            <TableHead>Aktual : standar</TableHead>
            <TableHead>Buffer di atas kebutuhan</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {factors.map((f) => (
            <TableRow key={f.material_id}>
              <TableCell className="font-medium">{code.get(f.material_id) ?? f.material_id}</TableCell>
              {f.waste_factor == null ? (
                <TableCell colSpan={2} className="text-muted-foreground">
                  Tidak terdefinisi (standar 0)
                </TableCell>
              ) : (
                <>
                  <TableCell className="tabular-nums">{f.waste_factor.toFixed(3)}</TableCell>
                  <TableCell className="tabular-nums">
                    {f.waste_factor > 1 ? `+${((f.waste_factor - 1) * 100).toFixed(1)}%` : "0% (tanpa waste)"}
                  </TableCell>
                </>
              )}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
