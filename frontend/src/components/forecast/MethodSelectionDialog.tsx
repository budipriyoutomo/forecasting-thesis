"use client";

import { useState } from "react";

import { FormError } from "@/components/common/FormError";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export interface MethodSelectionTarget {
  method: string;
  /** "kode — nama" produk, atau "semua produk" untuk pilihan massal. */
  label: string;
}

// Fase 11.15 — planner memilih metode forecast. Pilihan dicatat sebagai override append-only
// (AGENTS §5): alasan wajib, hasil forecast asli tidak diubah, riwayat tetap ada.
export function MethodSelectionDialog({
  target,
  onSubmit,
  onClose,
  pending = false,
  error = null,
}: {
  target: MethodSelectionTarget | null;
  onSubmit: (reason: string) => void;
  onClose: () => void;
  pending?: boolean;
  error?: string | null;
}) {
  return (
    <Dialog open={Boolean(target)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Pakai metode {target?.method}</DialogTitle>
          <DialogDescription>
            Untuk {target?.label}. Pilihan dicatat beserta alasannya dan bisa diganti kapan saja.
            Jalankan perencanaan persediaan lagi agar Reorder & Proyeksi Stok memakai metode ini.
          </DialogDescription>
        </DialogHeader>
        {target && (
          <ReasonForm
            key={`${target.label}-${target.method}`}
            onSubmit={onSubmit}
            pending={pending}
            error={error}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function ReasonForm({
  onSubmit,
  pending,
  error,
}: {
  onSubmit: (reason: string) => void;
  pending: boolean;
  error: string | null;
}) {
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (!reason.trim()) {
          setReasonError("Alasan wajib diisi");
          return;
        }
        setReasonError(null);
        onSubmit(reason.trim());
      }}
    >
      <div className="flex flex-col gap-2">
        <Label htmlFor="method-reason">Alasan</Label>
        <Textarea
          id="method-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Mis. MAPE paling kecil dan pola musiman tertangkap"
        />
        {reasonError && <p className="text-sm text-destructive">{reasonError}</p>}
      </div>
      <FormError message={error} />
      <div>
        <Button type="submit" disabled={pending}>
          {pending ? "Menyimpan…" : "Pakai metode"}
        </Button>
      </div>
    </form>
  );
}
