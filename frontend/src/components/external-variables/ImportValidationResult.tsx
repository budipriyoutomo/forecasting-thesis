"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { skippedSummary } from "@/lib/externalVariable";
import type { ImportDryRunResult } from "@/types/externalVariable";

// CR v3.4 §4.3 — hasil "Validasi file" (dry-run): semua error per baris sekaligus,
// bukan berhenti di error pertama, supaya planner bisa memperbaiki file dalam satu putaran.
export function ImportValidationResult({ result }: { result: ImportDryRunResult }) {
  const skipped = skippedSummary(result.skipped);
  const hidden = result.n_errors - result.errors.length;

  return (
    <Alert variant={result.valid ? "default" : "destructive"}>
      <AlertDescription className="flex flex-col gap-2">
        <p className="font-medium">
          {result.valid
            ? `File valid (format ${result.format === "wide" ? "lebar" : "panjang"}): ${result.imported} nilai siap diimpor.`
            : `${result.n_errors} error — perbaiki file lalu validasi ulang. Tidak ada data yang disimpan.`}
        </p>
        {result.errors.length > 0 && (
          <ul className="flex max-h-60 list-disc flex-col gap-0.5 overflow-y-auto pl-5 text-sm">
            {result.errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        )}
        {hidden > 0 && <p className="text-sm">{hidden} error lain tidak ditampilkan.</p>}
        {skipped && <p className="text-sm">{skipped}</p>}
        {result.warnings?.map((w) => (
          <p key={w} className="text-sm">
            {w}
          </p>
        ))}
      </AlertDescription>
    </Alert>
  );
}
