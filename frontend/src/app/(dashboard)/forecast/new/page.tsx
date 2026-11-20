"use client";

import Link from "next/link";

import { PageHeader } from "@/components/common/PageHeader";
import { PermissionGate } from "@/components/common/PermissionGate";
import { DemandTemplateCard } from "@/components/upload/DemandTemplateCard";
import { UploadHistory } from "@/components/upload/UploadHistory";
import { UploadPanel } from "@/components/upload/UploadPanel";
import { Button } from "@/components/ui/button";
import { useCan } from "@/hooks/usePermission";

export default function UploadPage() {
  const canRun = useCan("forecast.run");
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Upload Data Demand Produk"
        description="Unggah CSV histori demand produk jadi. Satu file boleh berisi banyak SKU."
        actions={
          canRun && (
            <Button variant="outline" asChild>
              <Link href="/forecast/new/config">Lanjut ke konfigurasi</Link>
            </Button>
          )
        }
      />

      {/* CR v3.5 §3.2: upload demand & run forecast hanya Admin/PPIC. */}
      <PermissionGate
        action="forecast.run"
        message="Hanya PPIC/Admin yang dapat menjalankan forecast."
        readHref="/material-arrivals"
        readLabel="Kedatangan Material"
      >
        <DemandTemplateCard />

        <UploadPanel />

        <section className="flex flex-col gap-3">
          <h2 className="text-lg font-medium">Riwayat Upload</h2>
          <UploadHistory />
        </section>
      </PermissionGate>
    </div>
  );
}
