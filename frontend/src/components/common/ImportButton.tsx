"use client";

import { Upload } from "lucide-react";
import { useId, useRef } from "react";

import { Button } from "@/components/ui/button";

// Tombol upload CSV/Excel bersama (Fase 11.2b+) — input file tersembunyi dipicu tombol.
// Nilai input direset setelah dipilih supaya file yang sama bisa diunggah ulang.
export function ImportButton({
  label,
  onFile,
  pending = false,
  accept = ".csv,.xlsx",
}: {
  label: string;
  onFile: (file: File) => void;
  pending?: boolean;
  accept?: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const id = useId();

  return (
    <>
      <input
        id={id}
        ref={ref}
        type="file"
        accept={accept}
        aria-label={label}
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.target.value = "";
        }}
      />
      <Button type="button" variant="outline" disabled={pending} onClick={() => ref.current?.click()}>
        <Upload />
        {pending ? "Mengimpor…" : label}
      </Button>
    </>
  );
}
