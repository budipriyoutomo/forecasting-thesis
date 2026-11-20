// CR v3.6 §8.6 — satu peta label status (run & hasil per produk) untuk semua badge,
// supaya tidak ada campuran "COMPLETED" (Inggris) dan "Selesai" di layar yang sama.
import type { BadgeProps } from "@/components/ui/badge";

export type StatusVariant = NonNullable<BadgeProps["variant"]>;

export interface StatusInfo {
  label: string;
  variant: StatusVariant;
}

const RUN_STATUS: Record<string, StatusInfo> = {
  PENDING: { label: "Menunggu", variant: "outline" },
  PROCESSING: { label: "Diproses", variant: "outline" },
  COMPLETED: { label: "Selesai", variant: "success" },
  FAILED: { label: "Gagal", variant: "destructive" },
};

const RESULT_STATUS: Record<string, StatusInfo> = {
  COMPLETED: { label: "Selesai", variant: "success" },
  INSUFFICIENT_DATA: { label: "Data kurang", variant: "destructive" },
  MODEL_SELECTION_FAILED: { label: "Semua metode gagal", variant: "destructive" },
};

const PENDING_SELECTION: StatusInfo = { label: "Belum dipilih", variant: "warning" };

export function runStatus(status: string): StatusInfo {
  return RUN_STATUS[status] ?? { label: status, variant: "outline" };
}

export function resultStatus(r: { status: string; selection_status?: string | null }): StatusInfo {
  if (r.status === "COMPLETED" && r.selection_status === "PENDING_SELECTION") return PENDING_SELECTION;
  return RESULT_STATUS[r.status] ?? { label: r.status, variant: "outline" };
}

export function isFailedResult(r: { status: string }): boolean {
  return r.status !== "COMPLETED";
}

export function isPendingResult(r: { status: string; selection_status?: string | null }): boolean {
  return r.status === "COMPLETED" && r.selection_status === "PENDING_SELECTION";
}
