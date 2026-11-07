"use client";

import { AuditTrail } from "@/components/override/AuditTrail";
import { OverrideForm } from "@/components/override/OverrideForm";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatNumber } from "@/lib/format";
import type { ReorderRecommendation } from "@/types/reorder";

const POLICY_LABEL: Record<string, string> = {
  eoq: "kelipatan EOQ",
  order_up_to: "order-up-to",
};

// Override qty pesan satu rekomendasi reorder (AGENTS §5: alasan wajib, append-only).
// Rekomendasi asli tidak berubah — override tercatat sebagai baris baru + tampil di riwayat.
export function ReorderOverrideDialog({
  runId,
  recommendation,
  materialLabel,
  onClose,
}: {
  runId: string | null;
  recommendation: ReorderRecommendation | null;
  materialLabel: string;
  onClose: () => void;
}) {
  const rec = recommendation;
  const policy = POLICY_LABEL[rec?.order_qty_policy_used ?? ""];

  return (
    <Dialog open={Boolean(rec?.id)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Override qty pesan</DialogTitle>
          <DialogDescription>
            {materialLabel} — qty sistem {formatNumber(rec?.recommended_order_qty ?? null)}
            {policy ? ` (${policy})` : ""}
            {rec?.override_qty != null ? ` · override berlaku ${formatNumber(rec.override_qty)}` : ""}.
            Rekomendasi asli tetap tersimpan; override dicatat beserta alasannya. Jalankan
            perencanaan lagi agar proyeksi stok memakai qty override.
          </DialogDescription>
        </DialogHeader>
        {rec?.id && (
          <>
            <OverrideForm
              key={rec.id}
              targetType="reorder_recommendation"
              targetId={rec.id}
              field="recommended_order_qty"
              label="Qty pesan baru"
              onDone={onClose}
            />
            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-medium">Riwayat override</h3>
              <AuditTrail targetId={rec.id} runId={runId} materialId={rec.material_id} />
            </section>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
