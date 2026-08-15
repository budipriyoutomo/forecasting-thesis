import type { ReactNode } from "react";

// Judul halaman yang seragam. Sebelumnya tiap page menulis <h1> sendiri dengan
// `justify-between` tanpa wrap, sehingga judul bertabrakan dengan tombol aksi di layar
// sempit — di sini aksi turun ke baris bawah saat ruang tidak cukup.
export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
