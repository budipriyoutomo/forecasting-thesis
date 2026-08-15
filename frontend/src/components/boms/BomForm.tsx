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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Bom, BomInput } from "@/types/bom";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";

const schema = z.object({
  product_id: z.string().min(1, "Produk wajib dipilih"),
  material_id: z.string().min(1, "Material wajib dipilih"),
  qty_per_unit: z.coerce.number().gt(0, "Harus lebih dari 0"),
});

type FormValues = z.infer<typeof schema>;

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
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      product_id: initial?.product_id ?? "",
      material_id: initial?.material_id ?? "",
      qty_per_unit: initial ? Number(initial.qty_per_unit) : ("" as unknown as number),
    },
  });

  const submit = form.handleSubmit((v) => onSubmit(v));

  return (
    <Form {...form}>
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <FormField
          control={form.control}
          name="product_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Produk</FormLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Pilih produk…" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {products.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.code} — {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="material_id"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Material</FormLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Pilih material…" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {materials.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.code} — {m.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="qty_per_unit"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Qty per unit produk</FormLabel>
              <FormControl>
                <Input type="number" step="any" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormError message={error} />

        <Button type="submit" disabled={submitting}>
          {submitting ? "Menyimpan…" : "Simpan"}
        </Button>
      </form>
    </Form>
  );
}
