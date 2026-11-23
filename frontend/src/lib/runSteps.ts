// CR v3.6 §4 — langkah detail run (stepper) diturunkan SEPENUHNYA dari data run
// (ringkasan run + ada/tidaknya proyeksi stok), bukan dari state lokal halaman, supaya
// refresh menampilkan posisi yang sama.
//
// Keputusan: perencanaan terkunci hanya bila BELUM ADA satu pun produk dengan metode
// berlaku. Bila sebagian masih menunggu pemilihan, perencanaan tetap boleh — produk itu
// dilewati (perilaku Fase 11.15) dan langkah 2 tetap ditandai "perlu tindakan".
import type { ForecastRunSummary } from "@/types/forecast";

// 23 Nov 2026: langkah "evaluation" (evaluasi usulan inventory) disisipkan setelah perencanaan.
export type RunStepKey = "forecast" | "select" | "planning" | "evaluation" | "reorder";
export type RunStepStatus = "done" | "todo" | "locked";

export interface RunStep {
  key: RunStepKey;
  label: string;
  status: RunStepStatus;
  /** Ringkas, tampil di bawah label (mis. "3 produk menunggu"). */
  hint?: string;
  /** Wajib bila status "locked" — prasyarat yang belum terpenuhi. */
  lockedReason?: string;
}

type RunCounts = Pick<ForecastRunSummary, "status" | "n_products" | "n_completed" | "n_failed"> & {
  n_pending_selection?: number;
};

export function deriveRunSteps({ run, hasPlanning }: { run: RunCounts; hasPlanning: boolean }): RunStep[] {
  const completed = run.status === "COMPLETED";
  const pending = run.n_pending_selection ?? 0;
  const selected = run.n_completed - pending;

  const forecast: RunStep = {
    key: "forecast",
    label: "Forecast",
    status: completed ? "done" : "todo",
    hint: completed ? `${run.n_completed} berhasil · ${run.n_failed} gagal` : "Run sedang diproses",
  };

  let select: RunStep;
  if (!completed) select = { key: "select", label: "Metode terbaik", status: "locked", lockedReason: "Tunggu run selesai." };
  else if (run.n_completed === 0)
    select = {
      key: "select",
      label: "Metode terbaik",
      status: "locked",
      lockedReason: "Tidak ada produk yang berhasil di-forecast — perbaiki data demand lalu buat run baru.",
    };
  else if (pending > 0) select = { key: "select", label: "Metode terbaik", status: "todo", hint: `${pending} produk menunggu` };
  else select = { key: "select", label: "Metode terbaik", status: "done", hint: `${selected} produk punya metode` };

  let planning: RunStep;
  if (select.status === "locked")
    planning = { key: "planning", label: "Perencanaan", status: "locked", lockedReason: select.lockedReason };
  else if (selected <= 0)
    planning = {
      key: "planning",
      label: "Perencanaan",
      status: "locked",
      lockedReason: `Pilih metode untuk ${pending} produk dulu.`,
    };
  else planning = { key: "planning", label: "Perencanaan", status: hasPlanning ? "done" : "todo" };

  const evaluation: RunStep = hasPlanning
    ? { key: "evaluation", label: "Evaluasi inventory", status: "done" }
    : {
        key: "evaluation",
        label: "Evaluasi inventory",
        status: "locked",
        lockedReason: "Jalankan perencanaan dulu (langkah 3) untuk menghitung evaluasi usulan inventory.",
      };

  const reorder: RunStep = hasPlanning
    ? { key: "reorder", label: "Reorder & gudang", status: "done" }
    : {
        key: "reorder",
        label: "Reorder & gudang",
        status: "locked",
        lockedReason: "Jalankan perencanaan dulu (langkah 3) untuk menghitung reorder & kapasitas gudang.",
      };

  return [forecast, select, planning, evaluation, reorder];
}

/** Langkah yang dibuka saat halaman dimuat: langkah pertama yang perlu tindakan, atau
 * langkah terakhir bila semua selesai. */
export function defaultStep(steps: RunStep[]): RunStepKey {
  return (steps.find((s) => s.status === "todo") ?? steps[steps.length - 1]).key;
}
