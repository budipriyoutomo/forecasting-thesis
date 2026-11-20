import { cn } from "@/lib/utils";

const STEPS = ["Data demand", "Produk & parameter", "Generate"] as const;

// CR v3.6 §4 — penanda wizard "Forecast baru": Data demand → Produk & parameter → Generate.
export function NewForecastSteps({ current }: { current: 0 | 1 | 2 }) {
  return (
    <ol className="flex flex-wrap items-center gap-2 text-sm" aria-label="Langkah forecast baru">
      {STEPS.map((label, i) => (
        <li key={label} className="flex items-center gap-2" aria-current={i === current ? "step" : undefined}>
          <span
            className={cn(
              "flex size-6 items-center justify-center rounded-full border text-xs font-semibold",
              i < current && "border-success bg-success text-success-foreground",
              i === current && "border-primary bg-primary text-primary-foreground",
            )}
          >
            {i + 1}
          </span>
          <span className={i === current ? "font-medium" : "text-muted-foreground"}>{label}</span>
          {i < STEPS.length - 1 && <span className="text-muted-foreground">→</span>}
        </li>
      ))}
    </ol>
  );
}
