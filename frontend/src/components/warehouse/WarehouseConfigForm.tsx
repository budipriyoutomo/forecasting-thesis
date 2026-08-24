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
import type { Product } from "@/types/product";
import type { WarehouseConfig, WarehouseConfigInput } from "@/types/warehouse";

const schema = z.object({
  product_id: z.string().min(1, "Produk wajib dipilih"),
  capacity_qty: z.coerce.number().gt(0, "Harus lebih dari 0"),
});

type FormValues = z.infer<typeof schema>;

// Kapasitas adalah angka bebas isian planner — bukan turunan luas gudang ×
// dimensi palet (keputusan user 24 Agustus 2026). Produk terkunci saat mode
// ubah karena satu produk hanya boleh punya satu baris kapasitas (unique).
export function WarehouseConfigForm({
  products,
  initial,
  onSubmit,
  submitting,
  error,
}: {
  products: Product[];
  initial?: WarehouseConfig;
  onSubmit: (input: WarehouseConfigInput) => void;
  submitting?: boolean;
  error?: string | null;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      product_id: initial?.product_id ?? "",
      capacity_qty: initial ? Number(initial.capacity_qty) : ("" as unknown as number),
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
              <Select
                value={field.value}
                onValueChange={field.onChange}
                disabled={Boolean(initial)}
              >
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
          name="capacity_qty"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Kapasitas gudang (unit produk)</FormLabel>
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
