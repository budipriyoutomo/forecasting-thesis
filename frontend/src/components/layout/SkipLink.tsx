export const MAIN_CONTENT_ID = "konten-utama";

// Sidebar menaruh belasan tautan sebelum konten. Tanpa jalan pintas ini, pengguna
// keyboard harus melewati semuanya di setiap halaman.
export function SkipLink() {
  return (
    <a
      href={`#${MAIN_CONTENT_ID}`}
      className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-ring"
    >
      Lewati ke konten utama
    </a>
  );
}
