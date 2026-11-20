import { EmptyState } from "@/components/common/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatNumber } from "@/lib/format";
import type { StockSnapshot } from "@/types/inventory";

// Riwayat snapshot stok ERP satu material (GET /stock-snapshots, CR v3.5 §5.2), terbaru di atas.
export function StockSnapshotHistory({ snapshots }: { snapshots: StockSnapshot[] }) {
  if (snapshots.length === 0) return <EmptyState message="Belum ada snapshot untuk material ini." />;
  const sorted = [...snapshots].sort((a, b) => b.snapshot_date.localeCompare(a.snapshot_date));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Tanggal snapshot</TableHead>
            <TableHead>Stok</TableHead>
            <TableHead>Satuan</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((s) => (
            <TableRow key={s.snapshot_date}>
              <TableCell>{formatDate(s.snapshot_date)}</TableCell>
              <TableCell className="tabular-nums">{formatNumber(s.qty)}</TableCell>
              <TableCell>{s.uom ?? "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
