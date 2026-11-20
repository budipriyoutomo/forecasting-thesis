"use client";

import Link from "next/link";

import { PageHeader } from "@/components/common/PageHeader";
import { PermissionGate } from "@/components/common/PermissionGate";
import { NewForecastSteps } from "@/components/forecast/NewForecastSteps";
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
        title="Forecast baru"
        description="Langkah 1 — unggah CSV histori demand produk jadi (satu file boleh berisi banyak SKU), atau lewati bila data sudah ada."
        actions={
          canRun && (
            <Button variant="outline" asChild>
              <Link href="/forecast/new/config">Lanjut: produk & parameter</Link>
            </Button>
          )
        }
      />

      {/* CR v3.5 §3.2: upload demand & run forecast hanya Admin/PPIC. */}
      <PermissionGate
        action="forecast.run"
        message="Hanya PPIC/Admin yang dapat menjalankan forecast."
        readHref="/forecast"
        readLabel="daftar forecast run"
      >
        <NewForecastSteps current={0} />

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
