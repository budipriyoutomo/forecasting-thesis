"use client";

import { UploadHistory } from "@/components/upload/UploadHistory";
import { UploadPanel } from "@/components/upload/UploadPanel";

export default function UploadPage() {
  return (
    <main className="container flex min-h-screen flex-col gap-8 py-16">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">Upload Data Konsumsi</h1>
        <p className="text-sm text-muted-foreground">
          Unggah CSV histori konsumsi (kolom: material_code, date, quantity). Satu file boleh berisi
          banyak material.
        </p>
      </div>

      <UploadPanel />

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Riwayat Upload</h2>
        <UploadHistory />
      </section>
    </main>
  );
}
