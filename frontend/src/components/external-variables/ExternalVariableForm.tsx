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
import { Textarea } from "@/components/ui/textarea";
import type { ExternalVariable, ExternalVariableInput } from "@/types/externalVariable";

// Kode dipakai langsung sebagai nama fitur ML → sama dengan validasi backend.
const schema = z.object({
  code: z
    .string()
    .regex(/^[a-z][a-z0-9_]{0,49}$/, "Kode harus snake_case huruf kecil, diawali huruf")
    .refine((c) => !/^(month|lag_\d+)$/.test(c), "Kode bentrok dengan fitur bawaan model"),
  name: z.string().min(1, "Nama wajib diisi"),
  value_type: z.enum(["numeric", "flag"]),
  scope: z.enum(["global", "product"]),
  unit: z.string().optional(),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const TYPE_OPTIONS = [
  { value: "numeric", label: "Numerik", hint: "Mis. suhu, harga, curah hujan" },
  { value: "flag", label: "Flag (0/1)", hint: "Mis. promosi, event, libur" },
] as const;

const SCOPE_OPTIONS = [
  { value: "global", label: "Global", hint: "Satu deret untuk semua produk (cuaca, musim)" },
  { value: "product", label: "Per produk", hint: "Nilai berbeda per SKU (harga, promo)" },
] as const;

export function ExternalVariableForm({
  initial,
  onSubmit,
  submitting,
  error,
}: {
  initial?: ExternalVariable;
  onSubmit: (input: ExternalVariableInput) => void;
  submitting?: boolean;
  error?: string | null;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      code: initial?.code ?? "",
      name: initial?.name ?? "",
      value_type: initial?.value_type ?? "numeric",
      scope: initial?.scope ?? "global",
      unit: initial?.unit ?? "",
      description: initial?.description ?? "",
    },
  });

  const submit = form.handleSubmit((v) => {
    const payload: ExternalVariableInput = {
      name: v.name,
      value_type: v.value_type,
      scope: v.scope,
      unit: v.unit || null,
      description: v.description || null,
    };
    onSubmit(initial ? payload : { ...payload, code: v.code });
  });

  return (
    <Form {...form}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <FormField
          control={form.control}
          name="code"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Kode</FormLabel>
              <FormControl>
                <Input placeholder="suhu" disabled={Boolean(initial)} {...field} />
              </FormControl>
              <FormDescription>Dipakai sebagai nama fitur model & kolom variable_code saat import.</FormDescription>
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
                <Input placeholder="Suhu rata-rata" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {(
          [
            ["value_type", "Tipe nilai", TYPE_OPTIONS],
            ["scope", "Cakupan", SCOPE_OPTIONS],
          ] as const
        ).map(([name, legend, options]) => (
          <FormField
            key={name}
            control={form.control}
            name={name}
            render={({ field }) => (
              <fieldset className="flex flex-col gap-2">
                <legend className="mb-1 text-sm font-medium">{legend}</legend>
                <div className="grid gap-2 sm:grid-cols-2">
                  {options.map((opt) => (
                    <label key={opt.value} className="flex cursor-pointer items-start gap-2 rounded-lg border p-3">
                      <input
                        type="radio"
                        name={name}
                        value={opt.value}
                        checked={field.value === opt.value}
                        onChange={() => field.onChange(opt.value)}
                        className="mt-1"
                      />
                      <span className="flex flex-col">
                        <span className="text-sm font-medium">{opt.label}</span>
                        <span className="text-xs text-muted-foreground">{opt.hint}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            )}
          />
        ))}
        <FormField
          control={form.control}
          name="unit"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Satuan</FormLabel>
              <FormControl>
                <Input placeholder="°C / Rp / mm" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Keterangan</FormLabel>
              <FormControl>
                <Textarea rows={2} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormError message={error ?? null} />
        <Button type="submit" disabled={submitting}>
          {submitting ? "Menyimpan…" : "Simpan variabel"}
        </Button>
      </form>
    </Form>
  );
}
