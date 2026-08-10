"use client";

import { useState } from "react";

import { OverrideForm } from "@/components/override/OverrideForm";
import { Button } from "@/components/ui/button";
import type { MaterialRequirement } from "@/types/forecast";

function fmt(value: string | null): string {
  if (value === null) return "—";
  return Number(value).toLocaleString("id-ID", { maximumFractionDigits: 2 });
}

function pct(value: string | null): string {
  if (value === null) return "—";
  return `${Number(value).toFixed(2)}%`;
}

// Kebutuhan raw material hasil breakdown BOM per run (Fase 5, dibaca Fase 9).
// Tiap baris bisa di-override planner — `target_id`-nya adalah `id` baris ini
// (AGENTS.md §5 "Planner Override — non-negotiable").
export function MaterialRequirementsTable({ requirements }: { requirements: MaterialRequirement[] }) {
  const [editing, setEditing] = useState<string | null>(null);

  if (requirements.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Belum ada kebutuhan material untuk run ini — produk yang diforecast belum punya BOM.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-2 pr-4 font-medium">Material</th>
            <th className="py-2 pr-4 font-medium">Kebutuhan (forecast)</th>
            <th className="py-2 pr-4 font-medium">Standar Pemakaian</th>
            <th className="py-2 pr-4 font-medium">Aktual Pemakaian</th>
            <th className="py-2 pr-4 font-medium">Buffer</th>
            <th className="py-2 font-medium">Aksi</th>
          </tr>
        </thead>
        <tbody>
          {requirements.map((req) => (
            <tr key={req.id} className="border-b align-top last:border-0">
              <td className="py-2 pr-4 font-medium">{req.material_id}</td>
              <td className="py-2 pr-4">{fmt(req.forecast_qty)}</td>
              <td className="py-2 pr-4">{fmt(req.standard_usage_qty)}</td>
              <td className="py-2 pr-4">{fmt(req.actual_usage_qty)}</td>
              <td className="py-2 pr-4">{pct(req.buffer_stock_pct)}</td>
              <td className="py-2">
                {editing === req.id ? (
                  <div className="min-w-56">
                    <OverrideForm
                      targetType="material_requirement"
                      targetId={req.id}
                      field="forecast_qty"
                      label="Kebutuhan material baru"
                      onDone={() => setEditing(null)}
                    />
                    <Button variant="ghost" onClick={() => setEditing(null)} className="mt-2">
                      Batal
                    </Button>
                  </div>
                ) : (
                  <Button variant="ghost" onClick={() => setEditing(req.id)}>
                    Override
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
