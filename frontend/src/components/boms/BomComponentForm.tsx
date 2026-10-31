"use client";

import { useState } from "react";

import { FormError } from "@/components/common/FormError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Material } from "@/types/material";

// Tambah komponen level 2 (mis. Preform ← Bottle) — Fase 11.3. Siklus ditolak backend (BOM_CYCLE_DETECTED).
export function BomComponentForm({
  parents,
  materials,
  onSubmit,
  submitting,
  error,
}: {
  parents: { id: string; code: string }[];
  materials: Material[];
  onSubmit: (input: { parentId: string; componentId: string; qty: number }) => void;
  submitting?: boolean;
  error?: string | null;
}) {
  const [parentId, setParentId] = useState("");
  const [componentId, setComponentId] = useState("");
  const [qty, setQty] = useState("1");
  const [invalid, setInvalid] = useState<string | null>(null);
  const select = "h-9 rounded-md border bg-transparent px-3 text-sm";

  return (
    <form
      className="grid gap-3 sm:grid-cols-[1fr_1fr_8rem_auto] sm:items-end"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        if (!parentId || !componentId) return setInvalid("Pilih material induk dan komponen");
        if (parentId === componentId) return setInvalid("Material tidak bisa menjadi komponen dirinya sendiri");
        if (!(Number(qty) > 0)) return setInvalid("Qty per unit harus lebih dari 0");
        setInvalid(null);
        onSubmit({ parentId, componentId, qty: Number(qty) });
      }}
    >
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="comp-parent">Material induk</Label>
        <select id="comp-parent" className={select} value={parentId} onChange={(e) => setParentId(e.target.value)}>
          <option value="">Pilih…</option>
          {parents.map((p) => (
            <option key={p.id} value={p.id}>
              {p.code}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="comp-child">Komponen</Label>
        <select id="comp-child" className={select} value={componentId} onChange={(e) => setComponentId(e.target.value)}>
          <option value="">Pilih…</option>
          {materials.map((m) => (
            <option key={m.id} value={m.id}>
              {m.code} — {m.name}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="comp-qty">Qty / unit</Label>
        <Input id="comp-qty" type="number" min={0} step="any" value={qty} onChange={(e) => setQty(e.target.value)} />
      </div>
      <Button type="submit" disabled={submitting}>
        {submitting ? "Menyimpan…" : "Tambah komponen"}
      </Button>
      <div className="sm:col-span-4">
        <FormError message={invalid ?? error ?? null} />
      </div>
    </form>
  );
}
