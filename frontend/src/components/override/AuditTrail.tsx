"use client";

import { EmptyState } from "@/components/common/EmptyState";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";
import { useAuditTrail, useReorderAuditTrail } from "@/hooks/useOverrides";

function nilai(value: Record<string, unknown> | null): string {
  if (!value) return "—";
  return Object.entries(value)
    .map(([k, v]) => `${k}: ${String(v)}`)
    .join(", ");
}

// Riwayat override (append-only): siapa, kapan, sebelum → sesudah, alasan.
// `targetId` = satu target; `runId` + `materialId` = seluruh override reorder material itu
// dalam satu run (v3.3, tetap lengkap setelah rekomendasi di-generate ulang).
export function AuditTrail({
  targetId = null,
  runId = null,
  materialId = null,
}: {
  targetId?: string | null;
  runId?: string | null;
  materialId?: string | null;
}) {
  const byContext = Boolean(runId && materialId);
  const single = useAuditTrail(byContext ? null : targetId);
  const context = useReorderAuditTrail(byContext ? runId : null, byContext ? materialId : null);
  const { data, isPending, isError } = byContext ? context : single;

  if (isPending) {
    return (
      <div className="flex flex-col gap-2" role="status">
        <span className="sr-only">Memuat riwayat…</span>
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Gagal memuat riwayat override.</AlertDescription>
      </Alert>
    );
  }

  if (!data || data.length === 0) {
    return <EmptyState message="Belum ada override." hint="Perubahan planner akan tercatat di sini." />;
  }

  return (
    <ol className="flex flex-col gap-3 border-l pl-4">
      {data.map((ov) => (
        <li key={ov.id} className="relative flex flex-col gap-1 text-sm">
          <span className="absolute -left-[21px] top-1.5 size-2 rounded-full bg-primary" />
          <p className="text-xs text-muted-foreground">{formatDate(ov.created_at)}</p>
          <p>
            <span className="text-muted-foreground">Sebelum:</span> {nilai(ov.previous_value)}
          </p>
          <p>
            <span className="text-muted-foreground">Sesudah:</span> {nilai(ov.new_value)}
          </p>
          <p className="rounded-md bg-muted/50 p-2">
            <span className="text-muted-foreground">Alasan:</span> {ov.reason}
          </p>
        </li>
      ))}
    </ol>
  );
}
