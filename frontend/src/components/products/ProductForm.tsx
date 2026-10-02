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
import { optionalPriceField, parsePrice, priceDefault } from "@/lib/price";
import type { Product, ProductInput } from "@/types/product";

const schema = z.object({
  code: z.string().min(1, "Kode wajib diisi"),
  name: z.string().min(1, "Nama wajib diisi"),
  category: z.string().optional(),
  unit: z.string().min(1, "Satuan wajib diisi"),
  cost_price: optionalPriceField,
  selling_price: optionalPriceField,
});

type FormValues = z.infer<typeof schema>;

export function ProductForm({
  initial,
  onSubmit,
  submitting,
  error,
}: {
  initial?: Product;
  onSubmit: (input: ProductInput) => void;
  submitting?: boolean;
  error?: string | null;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      code: initial?.code ?? "",
      name: initial?.name ?? "",
      category: initial?.category ?? "",
      unit: initial?.unit ?? "",
      cost_price: priceDefault(initial?.cost_price),
      selling_price: priceDefault(initial?.selling_price),
    },
  });

  const submit = form.handleSubmit((v) =>
    onSubmit({
      ...v,
      category: v.category?.trim() ? v.category : null,
      cost_price: parsePrice(v.cost_price),
      selling_price: parsePrice(v.selling_price),
    }),
  );

  return (
    <Form {...form}>
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <FormField
          control={form.control}
          name="code"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Kode SKU</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Nama</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="category"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Kategori</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="unit"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Satuan</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="cost_price"
            render={({ field }) => (
              <FormItem>
                <FormLabel>HPP (Rp / unit)</FormLabel>
                <FormControl>
                  <Input type="number" step="any" min={0} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="selling_price"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Harga jual (Rp / unit)</FormLabel>
                <FormControl>
                  <Input type="number" step="any" min={0} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormError message={error} />

        <Button type="submit" disabled={submitting}>
          {submitting ? "Menyimpan…" : "Simpan"}
        </Button>
      </form>
    </Form>
  );
}
