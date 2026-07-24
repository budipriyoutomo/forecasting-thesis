"use client";

import { cn } from "@/lib/utils";

// Kartu KPI ringkas untuk dashboard.
export function StatTile({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string | number;
  tone?: "default" | "urgent";
}) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold", tone === "urgent" && "text-destructive")}>
        {value}
      </p>
    </div>
  );
}
