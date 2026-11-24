"use client";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { MethodRowStatus } from "@/types/forecast";

const REASON: Record<Exclude<MethodRowStatus, "OK">, string> = {
  FAILED: "Metode gagal untuk varian ini",
  NO_SERIES: "Run lama: deret per metode tidak disimpan",
};

/** "—" + tooltip alasan (CR v3.7 §4.2). `reason` dari backend (alasan metode gagal) menggantikan
 *  teks umum. Butuh TooltipProvider di atasnya. */
export function MissingValue({ status, reason: detail }: { status: MethodRowStatus; reason?: string | null }) {
  const reason = status === "OK" ? null : (status === "FAILED" && detail) || REASON[status];
  if (!reason) return <span className="text-muted-foreground">—</span>;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0} aria-label={reason} className="cursor-help text-muted-foreground">
          —
        </span>
      </TooltipTrigger>
      <TooltipContent>{reason}</TooltipContent>
    </Tooltip>
  );
}
