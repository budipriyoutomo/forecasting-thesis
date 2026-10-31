"use client";

import { useState } from "react";

import { FormError } from "@/components/common/FormError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { MaterialReceiptInput } from "@/types/inventory";
import type { Material } from "@/types/material";

// Estimasi kedatangan material, input manual (Fase 11.5). Select native: daftar material pendek.
export function ReceiptForm({
  materials,
  onSubmit,
  submitting,
  error,
}: {
  materials: Material[];
  onSubmit: (input: MaterialReceiptInput) => void;
  submitting?: boolean;
  error?: string | null;
}) {
  const [materialId, setMaterialId] = useState("");
  const [date, setDate] = useState("");
  const [qty, setQty] = useState("");
  const [note, setNote] = useState("");
  const [invalid, setInvalid] = useState<string | null>(null);

  return (
    <form
      className="flex flex-col gap-3"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        if (!materialId) return setInvalid("Material wajib dipilih");
        if (!date) return setInvalid("Tanggal kedatangan wajib diisi");
        if (!(Number(qty) > 0)) return setInvalid("Qty harus lebih dari 0");
        setInvalid(null);
        onSubmit({ material_id: materialId, expected_date: date, qty: Number(qty), note: note.trim() || null });
      }}
    >
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="receipt-material">Material</Label>
        <select
          id="receipt-material"
          className="h-9 rounded-md border bg-transparent px-3 text-sm"
          value={materialId}
          onChange={(e) => setMaterialId(e.target.value)}
        >
          <option value="">Pilih material…</option>
          {materials.map((m) => (
            <option key={m.id} value={m.id}>
              {m.code} — {m.name}
            </option>
          ))}
        </select>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="receipt-date">Tanggal kedatangan</Label>
          <Input id="receipt-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="receipt-qty">Qty</Label>
          <Input id="receipt-qty" type="number" min={0} step="any" value={qty} onChange={(e) => setQty(e.target.value)} />
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="receipt-note">Catatan</Label>
        <Input id="receipt-note" placeholder="No. PO / supplier" value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
      <FormError message={invalid ?? error ?? null} />
      <Button type="submit" disabled={submitting}>
        {submitting ? "Menyimpan…" : "Simpan kedatangan"}
      </Button>
    </form>
  );
}
