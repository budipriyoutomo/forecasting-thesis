import type { Role } from "@/types/auth";

// Peta izin RBAC (CR v3.5 §3) — salinan dari backend/app/utils/permissions.py.
// backend/tests/unit/test_rbac.py mem-parse blok di bawah dan membandingkannya dengan
// peta backend, jadi pertahankan format `"action": ["role", ...]` satu baris per action.
// Dipakai untuk MENYEMBUNYIKAN tombol tulis; backend tetap penegak akhirnya (403).
export const PERMISSIONS = {
  "master.write": ["admin"],
  "settings.write": ["admin"],
  "extvar.define": ["admin"],
  "extvar.import": ["admin", "ppic"],
  "data.upload": ["admin", "ppic"],
  "data.import_stock": ["admin", "ppic"],
  "forecast.run": ["admin", "ppic"],
  "forecast.select": ["admin", "ppic"],
  "override.create": ["admin", "ppic"],
  "planning.run": ["admin", "ppic"],
  "capacity.adjust": ["admin", "ppic"],
  "user.manage": ["admin"],
} as const satisfies Record<string, readonly Role[]>;

export type Action = keyof typeof PERMISSIONS;

export const can = (role: Role | undefined, action: Action): boolean =>
  !!role && (PERMISSIONS[action] as readonly Role[]).includes(role);
