"use client";

import { useUploadHistory } from "@/hooks/useUploads";

export function UploadHistory() {
  const { data, isPending, isError } = useUploadHistory();

  if (isPending) return <p className="text-sm text-muted-foreground">Memuat riwayat…</p>;
  if (isError) return <p className="text-sm text-destructive">Gagal memuat riwayat upload.</p>;
  if (!data || data.length === 0)
    return <p className="text-sm text-muted-foreground">Belum ada upload.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-muted-foreground">
            <th className="py-2 pr-4">File</th>
            <th className="py-2 pr-4">Baris</th>
            <th className="py-2 pr-4">Material</th>
            <th className="py-2 pr-4">Status</th>
          </tr>
        </thead>
        <tbody>
          {data.map((s) => (
            <tr key={s.session_id} className="border-b">
              <td className="py-2 pr-4 font-medium">{s.file_name}</td>
              <td className="py-2 pr-4">{s.n_rows}</td>
              <td className="py-2 pr-4">{s.n_materials_detected}</td>
              <td className="py-2 pr-4">{s.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
