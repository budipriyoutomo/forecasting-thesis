"use client";

import type { WarehouseValidation } from "@/types/warehouse";

// Flag non-blocking (docs §6.7): melebihi kapasitas bukan error, hanya peringatan
// visual — keputusan tetap di tangan planner.
export function WarehouseCapacityBadge({ validation }: { validation: WarehouseValidation }) {
  const within = validation.is_within_capacity;
  const tone = within
    ? "border-green-500/40 bg-green-500/10 text-green-700 dark:text-green-400"
    : "border-destructive/40 bg-destructive/10 text-destructive";

  return (
    <div className={`rounded-md border px-3 py-2 text-sm ${tone}`}>
      <span className="font-medium">
        {within ? "Muat di gudang" : "Melebihi kapasitas gudang"}
      </span>{" "}
      · butuh {Number(validation.total_pallet_required).toFixed(1)} palet dari{" "}
      {Number(validation.total_pallet_capacity).toFixed(0)} tersedia
    </div>
  );
}
