"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useCreateOverride } from "@/hooks/useOverrides";
import type { OverrideTargetType } from "@/types/override";

// Form override planner — `reason` WAJIB (divalidasi di frontend & backend).
// `field`/`label` menentukan nilai baru yang di-override (mis. recommended_order_qty).
export function OverrideForm({
  targetType,
  targetId,
  field,
  label,
  onDone,
}: {
  targetType: OverrideTargetType;
  targetId: string;
  field: string;
  label: string;
  onDone?: () => void;
}) {
  const create = useCreateOverride();
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setReasonError("Alasan wajib diisi");
      return;
    }
    setReasonError(null);
    create.mutate(
      { target_type: targetType, target_id: targetId, new_value: { [field]: Number(value) }, reason },
      { onSuccess: () => onDone?.() },
    );
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="ov-value" className="text-sm font-medium">
          {label}
        </label>
        <input
          id="ov-value"
          type="number"
          step="any"
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="ov-reason" className="text-sm font-medium">
          Alasan override
        </label>
        <textarea
          id="ov-reason"
          className="min-h-20 rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        {reasonError && <p className="text-sm text-destructive">{reasonError}</p>}
      </div>

      {create.isError && <p className="text-sm text-destructive">{create.error.message}</p>}

      <Button type="submit" disabled={create.isPending}>
        {create.isPending ? "Menyimpan…" : "Simpan override"}
      </Button>
    </form>
  );
}
