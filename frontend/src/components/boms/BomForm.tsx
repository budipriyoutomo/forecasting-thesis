"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import type { Bom, BomInput } from "@/types/bom";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";

const schema = z.object({
  product_id: z.string().min(1, "Produk wajib dipilih"),
  material_id: z.string().min(1, "Material wajib dipilih"),
  qty_per_unit: z.coerce.number().gt(0, "Harus lebih dari 0"),
});

type FormValues = z.infer<typeof schema>;

const FIELD = "flex flex-col gap-1";
const INPUT = "h-10 rounded-md border border-input bg-background px-3 text-sm";

export function BomForm({
  products,
  materials,
  initial,
  onSubmit,
  submitting,
  error,
}: {
  products: Product[];
  materials: Material[];
  initial?: Bom;
  onSubmit: (input: BomInput) => void;
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
          product_id: initial.product_id,
          material_id: initial.material_id,
          qty_per_unit: Number(initial.qty_per_unit),
        }
      : {},
  });

  const submit = handleSubmit((v) => onSubmit(v));

  return (
    <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
      <div className={FIELD}>
        <label htmlFor="product_id" className="text-sm font-medium">
          Produk
        </label>
        <select id="product_id" className={INPUT} defaultValue="" {...register("product_id")}>
          <option value="" disabled>
            Pilih produk…
          </option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.code} — {p.name}
            </option>
          ))}
        </select>
        {errors.product_id && <p className="text-sm text-destructive">{errors.product_id.message}</p>}
      </div>

      <div className={FIELD}>
        <label htmlFor="material_id" className="text-sm font-medium">
          Material
        </label>
        <select id="material_id" className={INPUT} defaultValue="" {...register("material_id")}>
          <option value="" disabled>
            Pilih material…
          </option>
          {materials.map((m) => (
            <option key={m.id} value={m.id}>
              {m.code} — {m.name}
            </option>
          ))}
        </select>
        {errors.material_id && <p className="text-sm text-destructive">{errors.material_id.message}</p>}
      </div>

      <div className={FIELD}>
        <label htmlFor="qty_per_unit" className="text-sm font-medium">
          Qty per unit produk
        </label>
        <input
          id="qty_per_unit"
          type="number"
          step="any"
          className={INPUT}
          {...register("qty_per_unit")}
        />
        {errors.qty_per_unit && (
          <p className="text-sm text-destructive">{errors.qty_per_unit.message}</p>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button type="submit" disabled={submitting}>
        {submitting ? "Menyimpan…" : "Simpan"}
      </Button>
    </form>
  );
}
