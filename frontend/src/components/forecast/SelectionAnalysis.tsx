"use client";

import { Trophy } from "lucide-react";

import { METRIC_INFO } from "@/lib/metrics";
import { methodLabel } from "@/lib/methods";
import type { SelectionAnalysis as Analysis } from "@/types/forecast";

// 23 Nov 2026 — analisis kenapa sistem memilih metode terbaik (mode otomatis). Teks alasan
// disusun backend (`selection.py`); komponen ini hanya menampilkan. Sejak 23 Nov 2026 pilihan
// berlaku untuk seluruh produk (scope "global", rata-rata pengujian seluruh produk).
export function SelectionAnalysis({
  analysis,
  methodUsed,
}: {
  analysis: Analysis | null | undefined;
  methodUsed: string | null;
}) {
  if (!analysis) return null;
  const best = methodLabel(analysis.best_method);
  const label = (m: string) => METRIC_INFO[m as keyof typeof METRIC_INFO]?.label ?? m.toUpperCase();
  // Urutan dari backend = urutan prioritas (keputusan user 23 Nov 2026: MAD → MAPE → MFE).
  const priority = analysis.criteria.map((m, i) => `${i + 1}) ${label(m)}`).join(", ");
  const isGlobal = analysis.scope === "global" && (analysis.n_products ?? 1) > 1;
  const fallback = analysis.fallback_reason;
  const changed = !fallback && methodUsed && methodUsed !== analysis.best_method;

  return (
    <div className="rounded-md border-l-4 border-success bg-muted/50 p-3 text-sm">
      <p className="mb-1 flex items-center gap-2 font-medium">
        <Trophy className="size-4" aria-hidden />
        Kenapa {best} terbaik?
      </p>
      {isGlobal && (
        <p className="mb-1 text-xs font-medium">
          Berlaku untuk seluruh produk di run — dipilih dari rata-rata pengujian {analysis.n_products} produk.
        </p>
      )}
      <p className="text-muted-foreground">{analysis.summary}</p>
      {analysis.reasons.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
          {analysis.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      <p className="mt-2 text-xs text-muted-foreground">
        Urutan prioritas: {priority}
        {analysis.decided_by && <> · penentu: {label(analysis.decided_by)}</>}.
      </p>
      {fallback && <p className="mt-1 text-xs font-medium">{fallback}</p>}
      {changed && (
        <p className="mt-1 text-xs font-medium">
          Metode diganti planner ke {methodLabel(methodUsed)} — pilihan sistem tetap {best}.
        </p>
      )}
    </div>
  );
}
