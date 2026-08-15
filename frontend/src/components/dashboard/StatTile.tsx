"use client";

import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Kartu KPI ringkas untuk dashboard.
export function StatTile({
  label,
  value,
  tone = "default",
  hint,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  tone?: "default" | "urgent";
  hint?: string;
  icon?: LucideIcon;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        {Icon && <Icon className="size-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        {/* Kelas tone harus menempel di elemen nilai — dipakai test CostSummaryCard. */}
        <p
          className={cn(
            "text-2xl font-semibold tabular-nums",
            tone === "urgent" && "text-destructive",
          )}
        >
          {value}
        </p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}
