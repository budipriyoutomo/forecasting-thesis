"use client";

import { CircleAlert, CircleCheck } from "lucide-react";

import { Progress } from "@/components/ui/progress";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { WarehouseValidation } from "@/types/warehouse";

// Flag non-blocking (docs §6.7): melebihi kapasitas bukan error, hanya peringatan
// visual — keputusan tetap di tangan planner.
export function WarehouseCapacityBadge({ validation }: { validation: WarehouseValidation }) {
  const within = validation.is_within_capacity;
  const required = Number(validation.total_pallet_required);
  const capacity = Number(validation.total_pallet_capacity);
  // Dibatasi 100 supaya bar tidak meluber saat kebutuhan melebihi kapasitas —
  // status "melebihi" sudah disampaikan teks dan warna.
  const usage = capacity > 0 ? Math.min((required / capacity) * 100, 100) : 0;

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-lg border p-3 text-sm",
        within ? "border-success/40 bg-success/10" : "border-destructive/40 bg-destructive/10",
      )}
    >
      <div className="flex items-center gap-2">
        {within ? (
          <CircleCheck className="size-4 text-success" />
        ) : (
          <CircleAlert className="size-4 text-destructive" />
        )}
        <span className={cn("font-medium", within ? "text-success" : "text-destructive")}>
          {within ? "Muat di gudang" : "Melebihi kapasitas gudang"}
        </span>
        <span className="text-muted-foreground">
          · butuh {formatNumber(required, 1)} palet dari {formatNumber(capacity, 0)} tersedia
        </span>
      </div>
      <Progress
        value={usage}
        aria-label={`Pemakaian kapasitas gudang ${usage.toFixed(0)} persen`}
      />
    </div>
  );
}
