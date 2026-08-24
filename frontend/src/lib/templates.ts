// Template CSV untuk upload histori demand produk jadi.
//
// Kontrak kolom mengikuti backend/app/services/data_ingestion_service.py:
//   wajib   : product_code, period, actual
//   opsional: forecast_existing, planning  (pembanding baseline existing perusahaan)
// `period` juga menerima alias `date` di backend, tapi template selalu memakai
// `period` supaya user tidak perlu tahu soal alias.

export interface TemplateColumn {
  name: string;
  required: boolean;
  description: string;
  example: string;
}

export const DEMAND_TEMPLATE_COLUMNS: TemplateColumn[] = [
  {
    name: "product_code",
    required: true,
    description: "Kode produk jadi, sama dengan kode di master data produk.",
    example: "SKU-001",
  },
  {
    name: "period",
    required: true,
    description: "Awal periode, format YYYY-MM-DD. Umumnya awal bulan.",
    example: "2026-01-01",
  },
  {
    name: "forecast_existing",
    required: false,
    description: "Angka forecast metode lama perusahaan — dipakai sebagai pembanding.",
    example: "1150",
  },
  {
    name: "planning",
    required: false,
    description: "Rencana produksi setelah judgment planner.",
    example: "1200",
  },
  {
    name: "actual",
    required: true,
    description: "Realisasi demand/produksi. Ini angka yang dipelajari model.",
    example: "1180",
  },
];

export const DEMAND_TEMPLATE_FILENAME = "template-demand-produk.csv";

// Dua SKU × 6 bulan = 12 baris, di atas UPLOAD_MIN_ROWS (10) supaya template yang
// diunduh lalu langsung diunggah tidak ditolak INSUFFICIENT_DATA saat user mencoba.
const SAMPLE_ROWS: (string | number)[][] = [
  ["SKU-001", "2026-01-01", 1150, 1200, 1180],
  ["SKU-001", "2026-02-01", 1200, 1250, 1240],
  ["SKU-001", "2026-03-01", 1250, 1300, 1310],
  ["SKU-001", "2026-04-01", 1300, 1350, 1290],
  ["SKU-001", "2026-05-01", 1280, 1320, 1350],
  ["SKU-001", "2026-06-01", 1350, 1400, 1420],
  ["SKU-002", "2026-01-01", 480, 500, 510],
  ["SKU-002", "2026-02-01", 500, 520, 495],
  ["SKU-002", "2026-03-01", 510, 530, 545],
  ["SKU-002", "2026-04-01", 540, 560, 570],
  ["SKU-002", "2026-05-01", 560, 580, 555],
  ["SKU-002", "2026-06-01", 570, 600, 610],
];

/** Isi file template: header kontrak + contoh data yang tinggal ditimpa user. */
export function buildDemandTemplateCsv(): string {
  const header = DEMAND_TEMPLATE_COLUMNS.map((c) => c.name).join(",");
  const rows = SAMPLE_ROWS.map((r) => r.join(","));
  return [header, ...rows].join("\n") + "\n";
}
