import { clearToken } from "@/lib/auth";

// Sesi berakhir (CR v3.5 §5.3): request ber-token dibalas 401 (AUTH_TOKEN_EXPIRED, atau
// AUTH_INVALID_CREDENTIALS untuk token invalid) → hapus cookie lalu kembali ke login dengan
// `next` = halaman saat ini. Full navigation (bukan router.push) supaya cache TanStack Query
// milik sesi lama ikut terbuang.

const DEFAULT_AFTER_LOGIN = "/dashboard";
let redirecting = false;

function currentPath(): string {
  return typeof window === "undefined" ? "/" : `${window.location.pathname}${window.location.search}`;
}

function defaultNavigate(url: string) {
  window.location.assign(url);
}

export function handleSessionExpired(navigate: (url: string) => void = defaultNavigate, from: string = currentPath()) {
  clearToken();
  // Banyak query bisa gagal 401 bersamaan — cukup satu redirect; di /login tidak perlu.
  if (redirecting || from === "/login" || from.startsWith("/login?")) return;
  redirecting = true;
  navigate(`/login?next=${encodeURIComponent(from)}&reason=expired`);
}

/** Khusus test: state modul bertahan antar test dalam satu file. */
export function _resetSessionExpired() {
  redirecting = false;
}

/** Tujuan setelah login: hanya path relatif internal (cegah open redirect & loop ke /login). */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return DEFAULT_AFTER_LOGIN;
  if (next === "/login" || next.startsWith("/login?") || next.startsWith("/login/")) return DEFAULT_AFTER_LOGIN;
  return next;
}
