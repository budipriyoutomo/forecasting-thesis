"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormError } from "@/components/common/FormError";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import type { Material, MaterialInput } from "@/types/material";

const schema = z.object({
  code: z.string().min(1, "Kode wajib diisi"),
  name: z.string().min(1, "Nama wajib diisi"),
  category: z.string().optional(),
  unit: z.string().min(1, "Satuan wajib diisi"),
  lead_time_days: z.coerce.number().int().min(0, "Tidak boleh negatif"),
  moq: z.coerce.number().min(0, "Tidak boleh negatif"),
});

type FormValues = z.infer<typeof schema>;

export function MaterialForm({
  initial,
  onSubmit,
  submitting,
  error,
}: {
  initial?: Material;
  onSubmit: (input: MaterialInput) => void;
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
      lead_time_days: initial?.lead_time_days ?? 0,
      moq: initial ? Number(initial.moq) : 0,
    },
  });

  const submit = form.handleSubmit((v) =>
    onSubmit({ ...v, category: v.category?.trim() ? v.category : null }),
  );

  return (
    <Form {...form}>
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <FormField
          control={form.control}
          name="code"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Kode</FormLabel>
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
            name="lead_time_days"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Lead time (hari)</FormLabel>
                <FormControl>
                  <Input type="number" {...field} />
                </FormControl>
                <FormDescription>Dipakai menghitung reorder point.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="moq"
            render={({ field }) => (
              <FormItem>
                <FormLabel>MOQ</FormLabel>
                <FormControl>
                  <Input type="number" step="any" {...field} />
                </FormControl>
                <FormDescription>Batas bawah kuantitas pesanan.</FormDescription>
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
