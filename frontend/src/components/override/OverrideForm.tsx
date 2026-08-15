"use client";

import { useState } from "react";

import { FormError } from "@/components/common/FormError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
      {
        target_type: targetType,
        target_id: targetId,
        new_value: { [field]: Number(value) },
        reason,
      },
      { onSuccess: () => onDone?.() },
    );
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="ov-value">{label}</Label>
        <Input
          id="ov-value"
          type="number"
          step="any"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="ov-reason">Alasan override</Label>
        <Textarea
          id="ov-reason"
          className="min-h-20"
          aria-invalid={reasonError ? true : undefined}
          aria-describedby={reasonError ? "ov-reason-error" : undefined}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        {reasonError && (
          <p id="ov-reason-error" className="text-sm font-medium text-destructive">
            {reasonError}
          </p>
        )}
      </div>

      <FormError message={create.isError ? create.error.message : null} />

      <Button type="submit" disabled={create.isPending}>
        {create.isPending ? "Menyimpan…" : "Simpan override"}
      </Button>
    </form>
  );
}
