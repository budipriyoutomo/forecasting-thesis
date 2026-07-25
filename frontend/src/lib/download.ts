// Unduh file biner dari endpoint export (bukan envelope JSON) lalu trigger
// download di browser. Mengembalikan blob supaya mudah dites.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function downloadExport(path: string, token: string, fallbackName: string): Promise<Blob> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Export gagal (status ${res.status})`);
  }

  const blob = await res.blob();
  const filename = filenameFromDisposition(res.headers.get("Content-Disposition")) ?? fallbackName;

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);

  return blob;
}

function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;
  const match = header.match(/filename="?([^"]+)"?/);
  return match ? match[1] : null;
}
