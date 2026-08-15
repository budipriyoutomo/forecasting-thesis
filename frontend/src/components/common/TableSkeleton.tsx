import { Skeleton } from "@/components/ui/skeleton";

// Placeholder saat tabel sedang memuat, menggantikan teks "Memuat…" yang polos.
export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div role="status" className="flex flex-col gap-2 rounded-lg border p-4">
      <span className="sr-only">Memuat data…</span>
      <div data-slot="skeleton-grid" aria-hidden="true" className="flex flex-col gap-3">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} data-slot="skeleton-row" className="flex gap-3">
            {Array.from({ length: columns }).map((_, c) => (
              <Skeleton key={c} className="h-5 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
