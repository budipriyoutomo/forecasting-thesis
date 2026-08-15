"use client";

import Link from "next/link";

import { PageHeader } from "@/components/common/PageHeader";
import { UploadHistory } from "@/components/upload/UploadHistory";
import { UploadPanel } from "@/components/upload/UploadPanel";
import { Button } from "@/components/ui/button";

export default function UploadPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Upload Data Demand Produk"
        description="Unggah CSV histori demand produk jadi. Satu file boleh berisi banyak SKU."
        actions={
          <Button variant="outline" asChild>
            <Link href="/forecast/new/config">Lanjut ke konfigurasi</Link>
          </Button>
        }
      />

      <UploadPanel />

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Riwayat Upload</h2>
        <UploadHistory />
      </section>
    </div>
  );
}
