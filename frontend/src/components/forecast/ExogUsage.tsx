"use client";

import { Badge } from "@/components/ui/badge";
import { exogUsage } from "@/lib/externalVariable";

// CR v3.4 §4.2 — variabel eksternal yang benar-benar dipakai model ML vs yang di-drop
// (beserta alasannya), supaya klaim "model memakai variabel X" bisa diverifikasi.
export function ExogUsage({ hyperparameters }: { hyperparameters: Record<string, unknown> | null | undefined }) {
  const info = exogUsage(hyperparameters);
  if (!info) return null;

  return (
    <div className="flex flex-col gap-2 rounded-lg border p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={info.dropped.length ? "outline" : "secondary"}>
          {`Variabel eksternal dipakai ${info.used.length} / ${info.total}`}
        </Badge>
        {info.used.length > 0 && <span className="font-mono text-xs">{info.used.join(", ")}</span>}
      </div>
      {info.dropped.length > 0 && (
        <ul className="flex flex-col gap-1 text-muted-foreground">
          {info.dropped.map((d) => (
            <li key={d.code} className="flex flex-wrap gap-x-2">
              <span className="font-mono text-xs text-foreground">{d.code}</span>
              <span>— {d.reason}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
