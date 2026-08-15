"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormError } from "@/components/common/FormError";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import type { WarehouseConfig, WarehouseConfigInput } from "@/types/warehouse";

const schema = z.object({
  warehouse_area_m2: z.coerce.number().gt(0, "Harus lebih dari 0"),
  length: z.coerce.number().gt(0, "Harus lebih dari 0"),
  width: z.coerce.number().gt(0, "Harus lebih dari 0"),
  height: z.coerce.number().gt(0, "Harus lebih dari 0"),
});

type FormValues = z.infer<typeof schema>;

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
  // Nilai awal harus selalu terdefinisi. Dibiarkan undefined, `field.value` ikut
  // undefined dan `z.coerce.number()` menghasilkan NaN — zod lalu memunculkan pesan
  // tipe bawaannya, bukan "Harus lebih dari 0" yang dimaksud. String kosong
  // di-coerce jadi 0 sehingga aturan `.gt(0)` yang berbicara.
  const kosong = "" as unknown as number;
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: initial
      ? {
          warehouse_area_m2: Number(initial.warehouse_area_m2),
          length: initial.pallet_dimension.length,
          width: initial.pallet_dimension.width,
          height: initial.pallet_dimension.height,
        }
      : { warehouse_area_m2: kosong, length: kosong, width: kosong, height: kosong },
  });

  const submit = form.handleSubmit((v) =>
    onSubmit({
      warehouse_area_m2: v.warehouse_area_m2,
      pallet_dimension: { length: v.length, width: v.width, height: v.height },
    }),
  );

  return (
    <Form {...form}>
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <FormField
          control={form.control}
          name="warehouse_area_m2"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Luas gudang (m²)</FormLabel>
              <FormControl>
                <Input type="number" step="any" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-sm font-medium">Dimensi palet (m)</legend>
          <div className="grid grid-cols-3 gap-3">
            {(
              [
                ["length", "Panjang"],
                ["width", "Lebar"],
                ["height", "Tinggi"],
              ] as const
            ).map(([name, label]) => (
              <FormField
                key={name}
                control={form.control}
                name={name}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs text-muted-foreground">{label}</FormLabel>
                    <FormControl>
                      <Input type="number" step="any" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            ))}
          </div>
        </fieldset>

        <FormError message={error} />

        <Button type="submit" disabled={submitting}>
          {submitting ? "Menyimpan…" : "Simpan konfigurasi"}
        </Button>
      </form>
    </Form>
  );
}
