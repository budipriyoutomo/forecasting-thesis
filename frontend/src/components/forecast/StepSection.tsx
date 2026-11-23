import { ArrowLeft, ArrowRight } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { RunStep, RunStepKey } from "@/lib/runSteps";

// Kerangka seragam satu langkah di detail run: judul bernomor + deskripsi + aksi di kanan,
// isi, lalu navigasi bawah (Kembali / Lanjut) supaya posisi & gaya tombolnya konsisten di
// semua langkah. Tombol Lanjut hanya muncul bila langkah berikutnya tidak terkunci.
export function StepSection({
  index,
  steps,
  title,
  description,
  actions,
  nextLabel,
  onNavigate,
  children,
}: {
  index: number;
  steps: RunStep[];
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  /** Ganti teks tombol Lanjut (mis. "Lanjut: pilih metode untuk 3 produk"). */
  nextLabel?: string;
  onNavigate: (key: RunStepKey) => void;
  children: ReactNode;
}) {
  const id = `step-${steps[index].key}`;
  const prev = steps[index - 1];
  const next = steps[index + 1];
  return (
    <section className="flex flex-col gap-5" aria-labelledby={id}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b pb-4">
        {/* flex-1 + basis: judul mengisi sisa ruang dan aksi tetap di kanan selama muat; baru
            turun ke bawah bila area konten < ~20rem + lebar aksi. */}
        <div className="flex min-w-0 flex-1 basis-80 flex-col gap-1">
          <h2 id={id} className="text-lg font-semibold tracking-tight">
            {index + 1}. {title}
          </h2>
          {description && <p className="max-w-3xl text-sm text-muted-foreground">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
      </div>

      {children}

      {(prev || next) && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-4">
          {prev ? (
            <Button variant="ghost" onClick={() => onNavigate(prev.key)}>
              <ArrowLeft />
              Kembali: {prev.label}
            </Button>
          ) : (
            <span />
          )}
          {next && next.status !== "locked" && (
            <Button variant={next.status === "todo" ? "default" : "outline"} onClick={() => onNavigate(next.key)}>
              {nextLabel ?? `Lanjut: ${next.label}`}
              <ArrowRight />
            </Button>
          )}
        </div>
      )}
    </section>
  );
}
