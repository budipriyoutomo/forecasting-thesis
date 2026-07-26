"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import type { WarehouseConfig, WarehouseConfigInput } from "@/types/warehouse";

const schema = z.object({
  warehouse_area_m2: z.coerce.number().gt(0, "Harus lebih dari 0"),
  length: z.coerce.number().gt(0, "Harus lebih dari 0"),
  width: z.coerce.number().gt(0, "Harus lebih dari 0"),
  height: z.coerce.number().gt(0, "Harus lebih dari 0"),
});

type FormValues = z.infer<typeof schema>;

const FIELD = "flex flex-col gap-1";
const INPUT = "h-10 rounded-md border border-input bg-background px-3 text-sm";

export function WarehouseConfigForm({
  initial,
  onSubmit,
  submitting,
  error,
}: {
  initial?: WarehouseConfig | null;
  onSubmit: (input: WarehouseConfigInput) => void;
  submitting?: boolean;
  error?: string | null;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: initial
      ? {
          warehouse_area_m2: Number(initial.warehouse_area_m2),
          length: initial.pallet_dimension.length,
          width: initial.pallet_dimension.width,
          height: initial.pallet_dimension.height,
        }
      : undefined,
  });

  const submit = handleSubmit((v) =>
    onSubmit({
      warehouse_area_m2: v.warehouse_area_m2,
      pallet_dimension: { length: v.length, width: v.width, height: v.height },
    }),
  );

  return (
    <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
      <div className={FIELD}>
        <label htmlFor="warehouse_area_m2" className="text-sm font-medium">
          Luas gudang (m²)
        </label>
        <input id="warehouse_area_m2" type="number" step="any" className={INPUT} {...register("warehouse_area_m2")} />
        {errors.warehouse_area_m2 && (
          <p className="text-sm text-destructive">{errors.warehouse_area_m2.message}</p>
        )}
      </div>

      <fieldset className="grid grid-cols-3 gap-2">
        <legend className="mb-1 text-sm font-medium">Dimensi palet (m)</legend>
        <div className={FIELD}>
          <label htmlFor="length" className="text-xs text-muted-foreground">Panjang</label>
          <input id="length" type="number" step="any" className={INPUT} {...register("length")} />
        </div>
        <div className={FIELD}>
          <label htmlFor="width" className="text-xs text-muted-foreground">Lebar</label>
          <input id="width" type="number" step="any" className={INPUT} {...register("width")} />
        </div>
        <div className={FIELD}>
          <label htmlFor="height" className="text-xs text-muted-foreground">Tinggi</label>
          <input id="height" type="number" step="any" className={INPUT} {...register("height")} />
        </div>
      </fieldset>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button type="submit" disabled={submitting}>
        {submitting ? "Menyimpan…" : "Simpan konfigurasi"}
      </Button>
    </form>
  );
}
