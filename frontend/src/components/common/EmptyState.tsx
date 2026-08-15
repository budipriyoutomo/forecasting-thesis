import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

// Keadaan kosong yang seragam. `role="status"` supaya screen reader mengumumkan
// perubahan saat daftar berubah dari berisi menjadi kosong (mis. setelah difilter).
export function EmptyState({
  message,
  hint,
  action,
  className,
}: {
  message: string;
  hint?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="status"
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-8 text-center",
        className,
      )}
    >
      <p className="text-sm font-medium">{message}</p>
      {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
