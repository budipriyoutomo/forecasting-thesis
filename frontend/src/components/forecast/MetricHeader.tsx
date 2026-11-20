"use client";

import { Info } from "lucide-react";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { METRIC_INFO, type MetricKey } from "@/lib/metrics";

// CR v3.6 §2 — header kolom metrik + tooltip definisi singkat (sumber: lib/metrics.ts).
// Ikon info adalah tombol supaya bisa difokus keyboard; teks header tetap label metrik saja.
export function MetricHeader({ metric, label }: { metric: MetricKey; label?: string }) {
  const info = METRIC_INFO[metric];
  return (
    <span className="inline-flex items-center gap-1">
      {label ?? info.label}
      <TooltipProvider delayDuration={150}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-label={`Definisi ${info.label}`}
              className="rounded-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <Info className="size-3.5" aria-hidden />
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-left font-normal">{info.definition}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </span>
  );
}
