"use client";

import { useMe } from "@/hooks/useAuth";
import { can, type Action } from "@/lib/permissions";

// Boleh tidaknya user saat ini melakukan `action` (CR v3.5 §3.6). Selama profil
// belum dimuat hasilnya false — tombol tulis baru muncul setelah role diketahui.
export function useCan(action: Action): boolean {
  const { data: user } = useMe();
  return can(user?.role, action);
}
