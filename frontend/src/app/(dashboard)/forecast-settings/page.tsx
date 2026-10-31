"use client";

import { PageHeader } from "@/components/common/PageHeader";
import { ForecastSettingsForm } from "@/components/forecast-settings/ForecastSettingsForm";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useForecastSettings, useUpdateForecastSettings } from "@/hooks/useForecastSettings";
import { formatDate } from "@/lib/format";

export default function ForecastSettingsPage() {
  const { data, isPending, isError } = useForecastSettings();
  const update = useUpdateForecastSettings();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Pengaturan Forecast"
        description="Metode forecasting yang aktif dan metrik penentu metode pemenang Comparative Selection. Hasil forecast tetap menampilkan peringkat MAD, |MFE|, dan MAPE berdampingan sebagai acuan."
      />

      {isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat pengaturan forecast.</AlertDescription>
        </Alert>
      )}

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle className="text-base">Metode & metrik ranking</CardTitle>
          <CardDescription>
            Berlaku untuk forecast run berikutnya (mode otomatis). Run yang sudah ada tetap memakai
            metrik saat run dibuat.
            {data?.updated_at && <> Terakhir diubah {formatDate(data.updated_at)}.</>}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isPending ? (
            <Skeleton className="h-48 w-full" />
          ) : data ? (
            <ForecastSettingsForm
              key={data.updated_at ?? "default"}
              initial={data}
              available={data.available_methods}
              onSubmit={(input) => update.mutate(input)}
              pending={update.isPending}
              error={update.error?.message ?? null}
            />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
