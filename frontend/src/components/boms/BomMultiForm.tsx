"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "lucide-react";
import { useFieldArray, useForm } from "react-hook-form";
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
import type { BomBulkInput } from "@/types/bom";
import type { Material } from "@/types/material";
import type { Product } from "@/types/product";

const schema = z
  .object({
    product_id: z.string().min(1, "Produk wajib dipilih"),
    items: z
      .array(
        z.object({
          material_id: z.string().min(1, "Material wajib dipilih"),
          qty_per_unit: z.coerce.number().gt(0, "Harus lebih dari 0"),
        }),
      )
      .min(1),
  })
  .superRefine((v, ctx) => {
    const seen = new Set<string>();
    v.items.forEach((item, i) => {
      if (item.material_id && seen.has(item.material_id))
        ctx.addIssue({ code: "custom", path: ["items", i, "material_id"], message: "Material sudah dipilih di baris lain" });
      seen.add(item.material_id);
    });
  });

type FormValues = z.infer<typeof schema>;

const emptyRow = () => ({ material_id: "", qty_per_unit: "" as unknown as number });

// Tambah BOM untuk satu produk dengan banyak material sekaligus (19 Nov 2026) —
// dikirim ke POST /boms/bulk. Mode ubah tetap satu baris lewat BomForm.
export function BomMultiForm({
  products,
  materials,
  defaultProductId,
  onSubmit,
  submitting,
  error,
}: {
  products: Product[];
  materials: Material[];
  defaultProductId?: string;
  onSubmit: (input: BomBulkInput) => void;
  submitting?: boolean;
  error?: string | null;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { product_id: defaultProductId ?? "", items: [emptyRow()] },
  });
  const { fields, append, remove } = useFieldArray({ control: form.control, name: "items" });

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

        <div className="flex flex-col gap-3">
          {fields.map((row, i) => (
            <div key={row.id} className="grid grid-cols-[1fr_7rem_auto] items-start gap-2">
              <FormField
                control={form.control}
                name={`items.${i}.material_id`}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Material {i + 1}</FormLabel>
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
                name={`items.${i}.qty_per_unit`}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Qty {i + 1}</FormLabel>
                    <FormControl>
                      <Input type="number" step="any" min={0} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="mt-6"
                aria-label={`Hapus baris ${i + 1}`}
                disabled={fields.length === 1}
                hidden={fields.length === 1}
                onClick={() => remove(i)}
              >
                <X />
              </Button>
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" className="self-start" onClick={() => append(emptyRow())}>
            <Plus />
            Tambah material
          </Button>
        </div>

        <FormError message={error} />

        <Button type="submit" disabled={submitting}>
          {submitting ? "Menyimpan…" : `Simpan ${fields.length} material`}
        </Button>
      </form>
    </Form>
  );
}
