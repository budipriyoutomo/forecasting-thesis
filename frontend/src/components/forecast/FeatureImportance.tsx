"use client";

// Feature importance (embedded RF/XGBoost, Fase 11.2) — bobot ternormalisasi Σ = 1,
// backend sudah mengurutkan dari yang terpenting.
function featureLabel(name: string): string {
  if (name === "month") return "Bulan";
  const lag = /^lag_(\d+)$/.exec(name);
  return lag ? `Lag ${lag[1]}` : name;
}

export function FeatureImportance({ importance }: { importance: Record<string, number> | null }) {
  if (!importance || Object.keys(importance).length === 0) return null;
  const entries = Object.entries(importance);

  return (
    <div className="flex flex-col gap-2 rounded-lg border p-3">
      <p className="text-sm font-medium">Feature importance</p>
      <ul className="flex flex-col gap-1.5">
        {entries.map(([name, weight]) => (
          <li key={name} className="grid grid-cols-[7rem_1fr_3.5rem] items-center gap-2 text-sm">
            <span className="truncate">{featureLabel(name)}</span>
            <span className="h-2 rounded-full bg-muted">
              <span
                className="block h-2 rounded-full bg-primary"
                style={{ width: `${Math.max(weight * 100, 1)}%` }}
              />
            </span>
            <span className="text-right tabular-nums">{(weight * 100).toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
