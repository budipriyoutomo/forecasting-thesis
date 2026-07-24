"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
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

const FIELD = "flex flex-col gap-1";
const INPUT = "h-10 rounded-md border border-input bg-background px-3 text-sm";

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
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: initial
      ? {
          code: initial.code,
          name: initial.name,
          category: initial.category ?? "",
          unit: initial.unit,
          lead_time_days: initial.lead_time_days,
          moq: Number(initial.moq),
        }
      : { lead_time_days: 0, moq: 0 },
  });

  const submit = handleSubmit((v) =>
    onSubmit({ ...v, category: v.category?.trim() ? v.category : null }),
  );

  return (
    <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
      <div className={FIELD}>
        <label htmlFor="code" className="text-sm font-medium">
          Kode
        </label>
        <input id="code" className={INPUT} {...register("code")} />
        {errors.code && <p className="text-sm text-destructive">{errors.code.message}</p>}
      </div>

      <div className={FIELD}>
        <label htmlFor="name" className="text-sm font-medium">
          Nama
        </label>
        <input id="name" className={INPUT} {...register("name")} />
        {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
      </div>

      <div className={FIELD}>
        <label htmlFor="unit" className="text-sm font-medium">
          Satuan
        </label>
        <input id="unit" className={INPUT} {...register("unit")} />
        {errors.unit && <p className="text-sm text-destructive">{errors.unit.message}</p>}
      </div>

      <div className={FIELD}>
        <label htmlFor="lead_time_days" className="text-sm font-medium">
          Lead time (hari)
        </label>
        <input id="lead_time_days" type="number" className={INPUT} {...register("lead_time_days")} />
      </div>

      <div className={FIELD}>
        <label htmlFor="moq" className="text-sm font-medium">
          MOQ
        </label>
        <input id="moq" type="number" step="any" className={INPUT} {...register("moq")} />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button type="submit" disabled={submitting}>
        {submitting ? "Menyimpan…" : "Simpan"}
      </Button>
    </form>
  );
}
