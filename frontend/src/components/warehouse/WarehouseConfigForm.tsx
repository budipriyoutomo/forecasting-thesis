"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
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
import { formatNumber } from "@/lib/format";
import {
  CAPACITY_MODE_LABELS,
  computeEffectiveCapacity,
  isDusLike,
  usesDus,
  usesPallet,
} from "@/lib/warehouse";
import type { Product } from "@/types/product";
import type {
  CapacityMode,
  WarehouseCapacityInput,
  WarehouseConfig,
  WarehouseConfigInput,
} from "@/types/warehouse";

// Angka disimpan sebagai string di form supaya field kosong bisa dibedakan dari 0;
// dikonversi ke number saat submit.
const baseSchema = z.object({
  product_id: z.string().min(1, "Produk wajib dipilih"),
  capacity_mode: z.enum(["PALLET", "DUS", "COMBINED"]),
  pallet_qty: z.string(),
  dus_qty: z.string(),
  dus_per_pallet: z.string(),
  pcs_per_dus: z.string(),
});

type FormValues = z.infer<typeof baseSchema>;

const num = (v: string) => (v.trim() === "" ? null : Number(v));
const positive = (v: string) => {
  const n = num(v);
  return n !== null && Number.isFinite(n) && n > 0;
};

function toCapacityInput(v: FormValues, unit: string): WarehouseCapacityInput {
  const mode = v.capacity_mode as CapacityMode;
  return {
    capacity_mode: mode,
    pallet_qty: usesPallet(mode) ? (num(v.pallet_qty) ?? 0) : 0,
    dus_qty: usesDus(mode) ? (num(v.dus_qty) ?? 0) : 0,
    dus_per_pallet: usesPallet(mode) ? num(v.dus_per_pallet) : null,
    pcs_per_dus: unit && !isDusLike(unit) ? num(v.pcs_per_dus) : null,
  };
}

// Kapasitas diinput dalam pallet, dus, atau kombinasi (Fase 10, 2 Oktober 2026).
// `capacity_qty` resmi dihitung server; pratinjau di sini memakai rumus yang sama
// (lib/warehouse.ts). Produk terkunci saat mode ubah — satu produk satu baris.
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
  const unitOf = useMemo(() => {
    const byId = new Map(products.map((p) => [p.id, p.unit]));
    return (productId: string) => byId.get(productId) ?? "";
  }, [products]);

  const schema = useMemo(
    () =>
      baseSchema.superRefine((v, ctx) => {
        const mode = v.capacity_mode as CapacityMode;
        const unit = unitOf(v.product_id);
        const nonNegative = (field: "pallet_qty" | "dus_qty") => {
          const n = num(v[field]);
          if (n !== null && (!Number.isFinite(n) || n < 0))
            ctx.addIssue({ code: "custom", path: [field], message: "Tidak boleh negatif" });
        };
        if (usesPallet(mode)) {
          nonNegative("pallet_qty");
          if (!positive(v.dus_per_pallet))
            ctx.addIssue({
              code: "custom",
              path: ["dus_per_pallet"],
              message: "Dus per pallet wajib diisi (> 0)",
            });
        }
        if (usesDus(mode)) nonNegative("dus_qty");
        if (unit && !isDusLike(unit) && !positive(v.pcs_per_dus))
          ctx.addIssue({
            code: "custom",
            path: ["pcs_per_dus"],
            message: "Pcs per dus wajib diisi (> 0)",
          });

        const cap = computeEffectiveCapacity(toCapacityInput(v, unit || "DUS"), unit || "DUS");
        if (cap !== null && cap.dus <= 0)
          ctx.addIssue({
            code: "custom",
            path: [usesDus(mode) ? "dus_qty" : "pallet_qty"],
            message: "Kapasitas harus lebih dari 0",
          });
      }),
    [unitOf],
  );

  const str = (v: string | null | undefined) => (v == null ? "" : String(Number(v)));
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      product_id: initial?.product_id ?? "",
      capacity_mode: initial?.capacity_mode ?? "DUS",
      pallet_qty: initial && usesPallet(initial.capacity_mode) ? str(initial.pallet_qty) : "",
      dus_qty: initial && usesDus(initial.capacity_mode) ? str(initial.dus_qty) : "",
      dus_per_pallet: str(initial?.dus_per_pallet),
      pcs_per_dus: str(initial?.pcs_per_dus),
    },
  });

  const values = form.watch();
  const mode = values.capacity_mode as CapacityMode;
  const unit = unitOf(values.product_id);
  const needsPcs = Boolean(unit) && !isDusLike(unit);
  const preview = unit ? computeEffectiveCapacity(toCapacityInput(values, unit), unit) : null;

  const submit = form.handleSubmit((v) =>
    onSubmit({ product_id: v.product_id, ...toCapacityInput(v, unitOf(v.product_id)) }),
  );

  const numberField = (name: keyof FormValues, label: string) => (
    <FormField
      control={form.control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <FormControl>
            <Input type="number" step="any" min={0} {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );

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
          name="capacity_mode"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Mode kapasitas</FormLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {(Object.keys(CAPACITY_MODE_LABELS) as CapacityMode[]).map((m) => (
                    <SelectItem key={m} value={m}>
                      {CAPACITY_MODE_LABELS[m]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        {usesPallet(mode) && (
          <div className="grid grid-cols-2 gap-4">
            {numberField("pallet_qty", "Jumlah pallet")}
            {numberField("dus_per_pallet", "Dus per pallet")}
          </div>
        )}
        {usesDus(mode) && numberField("dus_qty", usesPallet(mode) ? "Jumlah dus lepas" : "Jumlah dus")}
        {needsPcs && numberField("pcs_per_dus", `Pcs per dus (unit produk: ${unit})`)}

        {preview && (
          <p className="text-sm text-muted-foreground" aria-live="polite">
            Kapasitas efektif:{" "}
            <span className="font-medium text-foreground tabular-nums">
              {formatNumber(preview.dus)} dus
            </span>
            {needsPcs && (
              <>
                {" "}
                ={" "}
                <span className="font-medium text-foreground tabular-nums">
                  {formatNumber(preview.qty)} {unit}
                </span>
              </>
            )}
          </p>
        )}

        <FormError message={error} />

        <Button type="submit" disabled={submitting}>
          {submitting ? "Menyimpan…" : "Simpan"}
        </Button>
      </form>
    </Form>
  );
}
