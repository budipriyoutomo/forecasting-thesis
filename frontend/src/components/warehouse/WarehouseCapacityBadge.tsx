"use client";

import { CircleAlert, CircleCheck } from "lucide-react";

import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Product } from "@/types/product";
import type { WarehouseValidation } from "@/types/warehouse";

// Flag non-blocking (docs §6.7): melebihi kapasitas bukan error, hanya peringatan
// visual — keputusan tetap di tangan planner. Validasi per PRODUK (kapasitas kini
// angka bebas, bukan agregat palet) — jadi produk mana yang bermasalah terlihat.
export function WarehouseCapacityBadge({
  validation,
  products,
}: {
  validation: WarehouseValidation;
  products: Product[];
}) {
  const within = validation.is_within_capacity;
  const details = validation.details;
  const productById = new Map(products.map((p) => [p.id, p]));

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-lg border p-3 text-sm",
        details.length === 0
          ? "border-muted-foreground/20 bg-muted/30"
          : within
            ? "border-success/40 bg-success/10"
            : "border-destructive/40 bg-destructive/10",
      )}
    >
      {details.length === 0 ? (
        <span className="text-muted-foreground">
          Belum ada produk yang bisa dibandingkan — pastikan produk pada run ini sudah
          punya konfigurasi kapasitas gudang.
        </span>
      ) : (
        <>
          <div className="flex items-center gap-2">
            {within ? (
              <CircleCheck className="size-4 text-success" />
            ) : (
              <CircleAlert className="size-4 text-destructive" />
            )}
            <span className={cn("font-medium", within ? "text-success" : "text-destructive")}>
              {within ? "Muat di gudang" : "Melebihi kapasitas gudang"}
            </span>
          </div>

          <div className="flex flex-col gap-2">
            {details.map((d) => {
              const product = productById.get(d.product_id);
              const label = product ? `${product.code} — ${product.name}` : d.product_id;
              return (
                <div
                  key={d.product_id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-background/60 px-2 py-1.5"
                >
                  <span className="font-medium">{label}</span>
                  <span
                    className={cn(
                      "text-xs",
                      d.is_within_capacity ? "text-muted-foreground" : "text-destructive font-medium",
                    )}
                  >
                    {formatNumber(d.required_qty)} / {formatNumber(d.capacity_qty)}
                    {!d.is_within_capacity && " · melebihi"}
                  </span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
