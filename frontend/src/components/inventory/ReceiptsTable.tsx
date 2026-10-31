"use client";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatNumber } from "@/lib/format";
import type { MaterialReceipt } from "@/types/inventory";
import type { Material } from "@/types/material";

export function ReceiptsTable({
  receipts,
  materials,
  onDelete,
}: {
  receipts: MaterialReceipt[];
  materials: Material[];
  onDelete?: (r: MaterialReceipt) => void;
}) {
  if (receipts.length === 0) return <EmptyState message="Belum ada rencana kedatangan material." />;
  const code = new Map(materials.map((m) => [m.id, m.code]));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tanggal</TableHead>
            <TableHead>Material</TableHead>
            <TableHead>Qty</TableHead>
            <TableHead>Sumber</TableHead>
            <TableHead>Catatan</TableHead>
            <TableHead>
              <span className="sr-only">Aksi</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {receipts.map((r) => (
            <TableRow key={r.id}>
              <TableCell>{formatDate(r.expected_date)}</TableCell>
              <TableCell className="font-medium">{code.get(r.material_id) ?? r.material_id}</TableCell>
              <TableCell className="tabular-nums">{formatNumber(r.qty)}</TableCell>
              <TableCell>
                <Badge variant="outline">{r.source === "upload" ? "Upload" : "Manual"}</Badge>
              </TableCell>
              <TableCell>{r.note ?? "—"}</TableCell>
              <TableCell className="text-right">
                {onDelete && (
                  <ConfirmDialog
                    trigger={
                      <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                        Hapus
                      </Button>
                    }
                    title="Hapus rencana kedatangan?"
                    description="Kedatangan ini tidak lagi ikut menambah stok pada proyeksi berikutnya. Tindakan ini tidak bisa dibatalkan."
                    confirmLabel="Ya, hapus kedatangan"
                    onConfirm={() => onDelete(r)}
                  />
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
