import type { Role } from "@/types/auth";

// Label & ringkasan akses per role (PRD FR-8.2, CR v3.5 §3) — dipakai halaman Manajemen User.
export const ROLES: { value: Role; label: string; description: string }[] = [
  { value: "admin", label: "Admin", description: "Semua akses: master data, pengaturan, user, plus seluruh akses PPIC." },
  { value: "ppic", label: "PPIC (Planner)", description: "Upload data, jalankan forecast, pilih metode, override, rencana & reorder." },
  { value: "purchasing", label: "Purchasing", description: "Lihat & export hasil (reorder, kedatangan material); tanpa aksi tulis." },
  { value: "viewer", label: "Viewer", description: "Lihat & export saja." },
];

export const roleLabel = (role: Role): string => ROLES.find((r) => r.value === role)?.label ?? role;
