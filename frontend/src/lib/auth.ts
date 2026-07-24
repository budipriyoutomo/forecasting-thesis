// Penyimpanan token di cookie (bukan localStorage) supaya middleware Next.js
// (berjalan di server/edge) bisa membacanya untuk proteksi route.
export const TOKEN_COOKIE = "fiq_token";

export function setToken(token: string) {
  // 24 jam, selaras JWT_EXPIRE_HOURS default backend. SameSite=Lax cukup untuk MVP.
  document.cookie = `${TOKEN_COOKIE}=${token}; path=/; max-age=${60 * 60 * 24}; SameSite=Lax`;
}

export function clearToken() {
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${TOKEN_COOKIE}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}
