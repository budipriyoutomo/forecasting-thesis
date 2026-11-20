import Link from "next/link";

import type { DashboardSummary } from "@/types/dashboard";

const SEGMENTS = [
  { key: "urgent", label: "Segera reorder", className: "bg-destructive" },
  { key: "safe", label: "Aman", className: "bg-success" },
  { key: "overstock", label: "Kelebihan stok", className: "bg-chart-4" },
] as const;

// CR v3.6 §3 — satu bar bertumpuk status reorder + angka langsung (bukan warna saja).
export function ReorderStatusBar({
  counts,
  href,
}: {
  counts: DashboardSummary["reorder_status_counts"];
  href?: string;
}) {
  const total = counts.urgent + counts.safe + counts.overstock;
  if (total === 0) return <p className="text-sm text-muted-foreground">Belum ada rekomendasi reorder.</p>;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
        {SEGMENTS.map((s) =>
          counts[s.key] > 0 ? (
            <div key={s.key} className={s.className} style={{ width: `${(counts[s.key] / total) * 100}%` }} />
          ) : null,
        )}
      </div>
      <ul className="grid gap-2 text-sm sm:grid-cols-3">
        {SEGMENTS.map((s) => (
          <li key={s.key} className="flex items-center gap-2">
            <span className={`size-2.5 rounded-full ${s.className}`} aria-hidden />
            <span>{s.label}</span>
            <span className="ml-auto font-semibold tabular-nums">{counts[s.key]}</span>
          </li>
        ))}
      </ul>
      {href && (
        <Link href={href} className="text-sm font-medium underline underline-offset-4">
          Lihat tabel reorder
        </Link>
      )}
    </div>
  );
}
