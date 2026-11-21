// Template CSV untuk setiap tombol import — supaya struktur file yang diunggah user tidak
// melenceng dari kontrak backend. Dibangun di browser (bukan endpoint baru): isinya statis.
// Pengecualian: variabel eksternal memakai template dinamis dari backend
// (GET /external-variables/template — header saja: period [+ product_code] + kode variabel aktif).
//
// Header kolom WAJIB sama persis dengan yang dibaca service backend (dicek di templates.test.ts):
//   demand          → backend/app/services/data_ingestion_service.py
//   stok ERP        → backend/app/services/inventory_data_service.py (StockSnapshotService)
//   pemakaian       → backend/app/services/material_usage_service.py

export interface TemplateColumn {
  name: string;
  required: boolean;
  /** Wajib dengan syarat (mis. "isi kolom A, ATAU B + C") — ditampilkan sebagai "Bersyarat". */
  conditional?: boolean;
  description: string;
  example: string;
}

export interface ImportTemplateSpec {
  title: string;
  filename: string;
  columns: TemplateColumn[];
  /** Contoh isian; `null` = sel sengaja dikosongkan. */
  sampleRows: (string | number | null)[][];
  /** Catatan cara pengisian, tampil di bawah tabel kolom. */
  notes: string[];
}

/** Isi file template: header kontrak + contoh data yang tinggal ditimpa user. */
export function buildTemplateCsv(spec: ImportTemplateSpec): string {
  const header = spec.columns.map((c) => c.name).join(",");
  const rows = spec.sampleRows.map((r) => r.map((v) => (v == null ? "" : String(v))).join(","));
  return [header, ...rows].join("\n") + "\n";
}

const COMMON_NOTES = [
  "Baris pertama (header) jangan diubah, dihapus, atau diterjemahkan — nama kolom harus persis sama.",
  "Hapus baris contoh lalu isi dengan data Anda. Simpan sebagai CSV (pemisah koma) atau .xlsx.",
  "Tanggal ditulis YYYY-MM-DD (mis. 2026-01-01). Hindari format 'Jan-26' yang bisa terbaca salah.",
];

// ── Demand produk jadi ─────────────────────────────────────────────────────────────
// `period` juga menerima alias `date` di backend, tapi template selalu memakai `period`.

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

export const DEMAND_TEMPLATE: ImportTemplateSpec = {
  title: "Template CSV",
  filename: DEMAND_TEMPLATE_FILENAME,
  columns: DEMAND_TEMPLATE_COLUMNS,
  // Dua SKU × 6 bulan = 12 baris, di atas UPLOAD_MIN_ROWS (10) supaya template yang
  // diunduh lalu langsung diunggah tidak ditolak INSUFFICIENT_DATA saat user mencoba.
  sampleRows: [
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
  ],
  notes: [
    ...COMMON_NOTES,
    "Satu file boleh berisi banyak SKU — cukup tambahkan baris baru dengan product_code berbeda.",
    "Minimal 10 baris data agar bisa diproses; satu baris = satu SKU di satu periode.",
    "Angka tanpa pemisah ribuan (1180, bukan 1.180). Kolom opsional boleh dikosongkan.",
  ],
};

/** Kompatibilitas: dipakai sebelum template digeneralisasi. */
export function buildDemandTemplateCsv(): string {
  return buildTemplateCsv(DEMAND_TEMPLATE);
}

// ── Stok ERP (snapshot) ────────────────────────────────────────────────────────────
// Backend juga menerima alias `date` untuk `snapshot_date`; template memakai nama kanonik.

export const STOCK_SNAPSHOT_TEMPLATE: ImportTemplateSpec = {
  title: "Template stok ERP",
  filename: "template-stok-erp.csv",
  columns: [
    {
      name: "material_code",
      required: true,
      description: "Kode material, sama dengan kode di master data material.",
      example: "MAT-001",
    },
    {
      name: "snapshot_date",
      required: true,
      description: "Tanggal posisi stok (hasil tarikan ERP), format YYYY-MM-DD.",
      example: "2026-10-31",
    },
    {
      name: "qty",
      required: true,
      description: "Jumlah stok on-hand pada tanggal tsb, dalam satuan master material. Tidak boleh negatif.",
      example: "1200",
    },
    {
      name: "uom",
      required: false,
      description: "Satuan sesuai ERP — hanya informasi, tidak mengonversi qty.",
      example: "PCS",
    },
  ],
  sampleRows: [
    ["MAT-001", "2026-10-31", 1200, "PCS"],
    ["MAT-002", "2026-10-31", 350.5, "KG"],
    ["MAT-001", "2026-11-30", 980, "PCS"],
  ],
  notes: [
    ...COMMON_NOTES,
    "Satu baris = satu material pada satu tanggal. Material + tanggal yang sama tidak boleh muncul dua kali dalam satu file.",
    "Material + tanggal yang sudah pernah diimpor akan ditimpa nilai baru.",
    "Angka memakai titik untuk desimal (350.5) dan tanpa pemisah ribuan (1200, bukan 1.200).",
    "Kode material yang belum terdaftar di master data membuat seluruh import ditolak.",
  ],
};

// ── Pemakaian aktual material ──────────────────────────────────────────────────────

export const MATERIAL_USAGE_TEMPLATE: ImportTemplateSpec = {
  title: "Template pemakaian",
  filename: "template-pemakaian-material.csv",
  columns: [
    {
      name: "material_code",
      required: true,
      description: "Kode material, sama dengan kode di master data material.",
      example: "MAT-001",
    },
    {
      name: "period",
      required: true,
      description: "Periode pemakaian, format YYYY-MM-DD. Disarankan tanggal 1 tiap bulan.",
      example: "2026-10-01",
    },
    {
      name: "actual_usage",
      required: true,
      description: "Pemakaian aktual material di periode tsb (termasuk waste/reject).",
      example: "1260",
    },
    {
      name: "standard_usage",
      required: false,
      conditional: true,
      description: "Pemakaian standar. Isi langsung DI SINI, atau kosongkan dan isi product_code + production_output.",
      example: "1200",
    },
    {
      name: "product_code",
      required: false,
      conditional: true,
      description: "Kode produk jadi pemakai material. Wajib bila standard_usage kosong (BOM produk → material harus ada).",
      example: "SKU-001",
    },
    {
      name: "production_output",
      required: false,
      conditional: true,
      description: "Jumlah produk jadi yang diproduksi. Bila standard_usage kosong, standar = output × qty BOM.",
      example: "1000",
    },
  ],
  sampleRows: [
    // Cara 1 — standar diisi langsung.
    ["MAT-001", "2026-10-01", 1260, 1200, null, null],
    // Cara 2 — standar dihitung sistem dari BOM.
    ["MAT-002", "2026-10-01", 530, null, "SKU-001", 1000],
  ],
  notes: [
    ...COMMON_NOTES,
    "Setiap baris pilih SALAH SATU cara: (1) isi standard_usage, atau (2) kosongkan standard_usage lalu isi product_code + production_output — standar dihitung dari BOM.",
    "Cara (2) hanya berhasil bila BOM produk → material tersebut sudah terdaftar.",
    "Material + produk + periode yang sama ditimpa nilai baru.",
    "Angka memakai titik untuk desimal, tanpa pemisah ribuan, dan tidak boleh negatif.",
    "Satu baris bermasalah membuat seluruh file ditolak — pesan error menyebut nomor barisnya.",
  ],
};
