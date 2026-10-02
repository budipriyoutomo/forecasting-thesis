"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useFieldArray, useForm, type Control } from "react-hook-form";
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
import { itemMonthlyCost } from "@/lib/costTemplate";
import { formatMoney } from "@/lib/format";
import type {
  CostItemType,
  CostTemplate,
  CostTemplateInput,
  CostTemplateItem,
} from "@/types/costTemplate";

// Angka disimpan sebagai string supaya field kosong bisa dibedakan dari 0.
const num = (v: string) => (v.trim() === "" ? null : Number(v));
const isNum = (v: string) => v.trim() !== "" && Number.isFinite(Number(v));

const requiredMoney = (label: string) =>
  z
    .string()
    .refine((v) => v.trim() !== "", `${label} wajib diisi`)
    .refine((v) => v.trim() === "" || (isNum(v) && Number(v) >= 0), "Harus angka ≥ 0");

const itemSchema = z.object({
  item_type: z.enum(["OVERHEAD", "STORAGE_ASSET"]),
  name: z.string().min(1, "Nama wajib diisi"),
  monthly_amount: z.string(),
  purchase_price: z.string(),
  salvage_value: z.string(),
  useful_life_months: z.string(),
  qty: z.string(),
});

const schema = z
  .object({
    name: z.string().min(1, "Nama wajib diisi"),
    description: z.string(),
    ordering_cost: requiredMoney("Biaya pesan"),
    holding_cost: requiredMoney("Biaya simpan"),
    items: z.array(itemSchema),
  })
  .superRefine((v, ctx) => {
    v.items.forEach((item, i) => {
      const issue = (field: keyof typeof item, message: string) =>
        ctx.addIssue({ code: "custom", path: ["items", i, field], message });
      if (!isNum(item.qty) || Number(item.qty) <= 0) issue("qty", "Jumlah harus > 0");
      if (item.item_type === "OVERHEAD") {
        if (!isNum(item.monthly_amount) || Number(item.monthly_amount) < 0)
          issue("monthly_amount", "Biaya per bulan wajib diisi (≥ 0)");
        return;
      }
      if (!isNum(item.purchase_price) || Number(item.purchase_price) < 0)
        issue("purchase_price", "Harga beli wajib diisi (≥ 0)");
      if (!isNum(item.useful_life_months) || Number(item.useful_life_months) <= 0)
        issue("useful_life_months", "Umur wajib diisi (> 0 bulan)");
      if (item.salvage_value.trim() !== "") {
        if (!isNum(item.salvage_value) || Number(item.salvage_value) < 0)
          issue("salvage_value", "Nilai sisa harus angka ≥ 0");
        else if (isNum(item.purchase_price) && Number(item.salvage_value) > Number(item.purchase_price))
          issue("salvage_value", "Nilai sisa tidak boleh melebihi harga beli");
      }
    });
  });

type FormValues = z.infer<typeof schema>;
type ItemValues = FormValues["items"][number];

const str = (v: string | number | null | undefined) => (v == null ? "" : String(Number(v)));

function itemDefaults(item_type: CostItemType, initial?: CostTemplateItem): ItemValues {
  return {
    item_type,
    name: initial?.name ?? "",
    monthly_amount: str(initial?.monthly_amount),
    purchase_price: str(initial?.purchase_price),
    salvage_value: str(initial?.salvage_value),
    useful_life_months: str(initial?.useful_life_months),
    qty: initial ? str(initial.qty) : "1",
  };
}

function toInput(v: FormValues): CostTemplateInput {
  return {
    name: v.name.trim(),
    description: v.description.trim() || null,
    ordering_cost: Number(v.ordering_cost),
    holding_cost: Number(v.holding_cost),
    items: v.items.map((item) => {
      const overhead = item.item_type === "OVERHEAD";
      return {
        item_type: item.item_type,
        name: item.name.trim(),
        monthly_amount: overhead ? num(item.monthly_amount) : null,
        purchase_price: overhead ? null : num(item.purchase_price),
        salvage_value: overhead ? null : (num(item.salvage_value) ?? 0),
        useful_life_months: overhead ? null : num(item.useful_life_months),
        qty: Number(item.qty),
      };
    }),
  };
}

function NumberField({
  control,
  name,
  label,
  description,
}: {
  control: Control<FormValues>;
  name: `items.${number}.${keyof ItemValues}` | "ordering_cost" | "holding_cost";
  label: string;
  description?: string;
}) {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <FormControl>
            <Input type="number" step="any" min={0} {...field} />
          </FormControl>
          {description && <FormDescription>{description}</FormDescription>}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

// Master template biaya (Fase 10): S & H dipakai EOQ bila template aktif. Overhead &
// depresiasi aset penyimpanan hanya referensi untuk saran H — lihat ringkasan.
export function CostTemplateForm({
  initial,
  onSubmit,
  submitting,
  error,
}: {
  initial?: CostTemplate;
  onSubmit: (input: CostTemplateInput) => void;
  submitting?: boolean;
  error?: string | null;
}) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initial?.name ?? "",
      description: initial?.description ?? "",
      ordering_cost: str(initial?.ordering_cost),
      holding_cost: str(initial?.holding_cost),
      items: (initial?.items ?? []).map((i) => itemDefaults(i.item_type, i)),
    },
  });
  const { fields, append, remove } = useFieldArray({ control: form.control, name: "items" });
  const items = form.watch("items");

  const section = (type: CostItemType, title: string, label: string, hint: string) => {
    const indexes = fields.map((_, i) => i).filter((i) => items[i]?.item_type === type);
    return (
      <fieldset className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div>
            <legend className="text-sm font-medium">{title}</legend>
            <p className="text-xs text-muted-foreground">{hint}</p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => append(itemDefaults(type))}
          >
            <Plus />
            Tambah {label.toLowerCase()}
          </Button>
        </div>
        {indexes.map((index, n) => {
          const item = items[index];
          const cost = itemMonthlyCost({
            item_type: type,
            monthly_amount: num(item.monthly_amount),
            purchase_price: num(item.purchase_price),
            salvage_value: num(item.salvage_value),
            useful_life_months: num(item.useful_life_months),
            qty: Number(item.qty) || 0,
          });
          return (
            <div
              key={fields[index].id}
              role="group"
              aria-label={`${label} ${n + 1}`}
              className="flex flex-col gap-3 rounded-md border p-3"
            >
              <div className="flex items-start gap-2">
                <div className="flex-1">
                  <FormField
                    control={form.control}
                    name={`items.${index}.name`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Nama</FormLabel>
                        <FormControl>
                          <Input
                            placeholder={type === "OVERHEAD" ? "Listrik, air, keamanan…" : "Pallet, rak, forklift…"}
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label="Hapus item"
                  className="mt-6 text-destructive hover:text-destructive"
                  onClick={() => remove(index)}
                >
                  <Trash2 />
                </Button>
              </div>
              {type === "OVERHEAD" ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <NumberField control={form.control} name={`items.${index}.monthly_amount`} label="Biaya per bulan (Rp)" />
                  <NumberField control={form.control} name={`items.${index}.qty`} label="Jumlah" />
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  <NumberField control={form.control} name={`items.${index}.purchase_price`} label="Harga beli / unit (Rp)" />
                  <NumberField control={form.control} name={`items.${index}.salvage_value`} label="Nilai sisa / unit (Rp)" />
                  <NumberField control={form.control} name={`items.${index}.useful_life_months`} label="Umur ekonomis (bulan)" />
                  <NumberField control={form.control} name={`items.${index}.qty`} label="Jumlah" />
                </div>
              )}
              {cost !== null && (
                <p className="text-right text-sm tabular-nums text-muted-foreground">
                  {formatMoney(cost)} / bulan
                </p>
              )}
            </div>
          );
        })}
      </fieldset>
    );
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((v) => onSubmit(toInput(v)))}
        className="flex flex-col gap-5"
        noValidate
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Nama template</FormLabel>
              <FormControl>
                <Input placeholder="mis. Biaya gudang 2026" {...field} />
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
              <FormLabel>Deskripsi</FormLabel>
              <FormControl>
                <Textarea rows={2} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <NumberField
            control={form.control}
            name="ordering_cost"
            label="Biaya pesan / pesanan (S, Rp)"
            description="Dipakai EOQ bila template aktif."
          />
          <NumberField
            control={form.control}
            name="holding_cost"
            label="Biaya simpan / unit / bulan (H, Rp)"
            description="Isian manual — lihat saran H di ringkasan."
          />
        </div>

        {section("OVERHEAD", "Biaya overhead", "Overhead", "Biaya rutin per bulan: listrik, air, keamanan, dll.")}
        {section(
          "STORAGE_ASSET",
          "Biaya penyimpanan (depresiasi aset)",
          "Aset",
          "Pallet, rak, alat handling — disusutkan garis lurus per bulan.",
        )}

        <FormError message={error} />

        <Button type="submit" disabled={submitting}>
          {submitting ? "Menyimpan…" : "Simpan template"}
        </Button>
      </form>
    </Form>
  );
}
