"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

// Verifikasi konektivitas frontend → backend (kriteria selesai Fase 0,
// docs/TASK_BREAKDOWN.md): memanggil GET /health lewat API client.
export function BackendStatus() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
  });

  if (isPending) {
    return <p className="text-sm text-muted-foreground">Mengecek koneksi backend…</p>;
  }

  const connected = !isError && data?.success === true;

  return (
    <p className={cn("text-sm font-medium", connected ? "text-foreground" : "text-destructive")}>
      {connected ? "Backend terhubung" : "Backend tidak terhubung"}
    </p>
  );
}
