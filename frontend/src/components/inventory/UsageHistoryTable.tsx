import { EmptyState } from "@/components/common/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatNumber } from "@/lib/format";
import type { MaterialUsageRow } from "@/types/inventory";
import type { Product } from "@/types/product";

// Riwayat pemakaian aktual vs standar satu material (GET /material-usage, CR v3.5 §5.2) —
// dasar faktor waste / buffer stock. Rasio = aktual ÷ standar per periode.
export function UsageHistoryTable({ rows, products }: { rows: MaterialUsageRow[]; products: Product[] }) {
  if (rows.length === 0) return <EmptyState message="Belum ada data pemakaian untuk material ini." />;
  const code = new Map(products.map((p) => [p.id, p.code]));
  const sorted = [...rows].sort((a, b) => b.period.localeCompare(a.period));
  return (
    <div className="overflow-x-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Periode</TableHead>
            <TableHead>Produk</TableHead>
            <TableHead>Output produksi</TableHead>
            <TableHead>Pemakaian standar</TableHead>
            <TableHead>Pemakaian aktual</TableHead>
            <TableHead>Aktual ÷ standar</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((r, i) => {
            const ratio = r.standard_usage && r.actual_usage != null ? r.actual_usage / r.standard_usage : null;
            return (
              <TableRow key={`${r.period}-${r.product_id ?? "material"}-${i}`}>
                <TableCell>{formatDate(r.period)}</TableCell>
                <TableCell>{r.product_id ? (code.get(r.product_id) ?? r.product_id) : "—"}</TableCell>
                <TableCell className="tabular-nums">{formatNumber(r.production_output)}</TableCell>
                <TableCell className="tabular-nums">{formatNumber(r.standard_usage)}</TableCell>
                <TableCell className="tabular-nums">{formatNumber(r.actual_usage)}</TableCell>
                <TableCell className="tabular-nums">{ratio === null ? "—" : `${(ratio * 100).toFixed(1)}%`}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
