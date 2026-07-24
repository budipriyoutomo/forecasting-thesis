"use client";

import { useAuditTrail } from "@/hooks/useOverrides";

// Riwayat override satu target (append-only): siapa, kapan, sebelum → sesudah, alasan.
export function AuditTrail({ targetId }: { targetId: string }) {
  const { data, isPending, isError } = useAuditTrail(targetId);

  if (isPending) return <p className="text-sm text-muted-foreground">Memuat riwayat…</p>;
  if (isError) return <p className="text-sm text-destructive">Gagal memuat riwayat override.</p>;
  if (!data || data.length === 0)
    return <p className="text-sm text-muted-foreground">Belum ada override.</p>;

  return (
    <ul className="flex flex-col gap-2">
      {data.map((ov) => (
        <li key={ov.id} className="rounded-md border p-3 text-sm">
          <p className="text-muted-foreground">
            {ov.created_at ? new Date(ov.created_at).toLocaleString("id-ID") : "—"}
          </p>
          <p>
            <span className="text-muted-foreground">Sebelum:</span> {JSON.stringify(ov.previous_value)}
          </p>
          <p>
            <span className="text-muted-foreground">Sesudah:</span> {JSON.stringify(ov.new_value)}
          </p>
          <p>
            <span className="text-muted-foreground">Alasan:</span> {ov.reason}
          </p>
        </li>
      ))}
    </ul>
  );
}
