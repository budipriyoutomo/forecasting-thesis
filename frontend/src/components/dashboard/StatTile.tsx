"use client";

import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface StatTrend {
  /** Teks delta siap tampil, mis. "−0,12 vs run sebelumnya". */
  label: string;
  direction: "up" | "down" | "flat";
  /** true = perubahan ini baik (hijau), false = buruk (merah); undefined = netral. */
  good?: boolean;
}

// Kartu KPI ringkas untuk dashboard. CR v3.6 §8.4: `trend` opsional (delta vs run
// sebelumnya) dan `href` opsional (tile jadi tautan ke rincian).
export function StatTile({
  label,
  value,
  tone = "default",
  hint,
  icon: Icon,
  trend,
  href,
}: {
  label: string;
  value: string | number;
  tone?: "default" | "urgent";
  hint?: string;
  icon?: LucideIcon;
  trend?: StatTrend;
  href?: string;
}) {
  const TrendIcon = trend?.direction === "up" ? ArrowUpRight : trend?.direction === "down" ? ArrowDownRight : ArrowRight;
  const card = (
    <Card className={cn("h-full", href && "transition-colors hover:bg-muted/40")}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        {Icon && <Icon className="size-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        {/* Kelas tone harus menempel di elemen nilai — dipakai test CostSummaryCard. */}
        <p className={cn("text-2xl font-semibold tabular-nums", tone === "urgent" && "text-destructive")}>{value}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
        {trend && (
          <p
            className={cn(
              "mt-1 inline-flex items-center gap-1 text-xs",
              trend.good === true && "text-success",
              trend.good === false && "text-destructive",
              trend.good === undefined && "text-muted-foreground",
            )}
          >
            <TrendIcon className="size-3.5" aria-hidden />
            {trend.label}
          </p>
        )}
      </CardContent>
    </Card>
  );
  return href ? (
    <Link href={href} className="rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
      {card}
    </Link>
  ) : (
    card
  );
}
