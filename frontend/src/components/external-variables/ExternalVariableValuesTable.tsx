import { EmptyState } from "@/components/common/EmptyState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatNumber } from "@/lib/format";
import type { ExternalScope, ExternalVariableValue } from "@/types/externalVariable";
import type { Product } from "@/types/product";

// Nilai per periode satu variabel eksternal (GET /external-variables/{id}/values, CR v3.5 §5.2).
export function ExternalVariableValuesTable({
  values,
  scope,
  products,
}: {
  values: ExternalVariableValue[];
  scope: ExternalScope;
  products: Product[];
}) {
  if (values.length === 0) {
    return <EmptyState message="Belum ada nilai." hint="Isi lewat Import nilai (format lebar atau panjang)." />;
  }
  const code = new Map(products.map((p) => [p.id, p.code]));
  const perProduct = scope === "product";
  const sorted = [...values].sort(
    (a, b) =>
      b.period.localeCompare(a.period) ||
      (code.get(a.product_id ?? "") ?? "").localeCompare(code.get(b.product_id ?? "") ?? ""),
  );
  return (
    <div className="max-h-[60vh] overflow-auto rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Periode</TableHead>
            {perProduct && <TableHead>Produk</TableHead>}
            <TableHead>Nilai</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((v) => (
            <TableRow key={`${v.period}-${v.product_id ?? "global"}`}>
              <TableCell>{formatDate(v.period)}</TableCell>
              {perProduct && <TableCell>{v.product_id ? (code.get(v.product_id) ?? v.product_id) : "—"}</TableCell>}
              <TableCell className="tabular-nums">{formatNumber(v.value, 4)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
