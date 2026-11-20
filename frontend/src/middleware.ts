import { NextResponse, type NextRequest } from "next/server";

import { TOKEN_COOKIE } from "@/lib/auth";
import { NAV_GROUPS } from "@/lib/navigation";

// Proteksi route grup (dashboard): tanpa token cookie → redirect ke /login.
// Middleware jalan di edge/server, jadi token disimpan di cookie (bukan localStorage).
//
// Prefix diturunkan dari navigasi sidebar (segmen pertama tiap `href`, mis.
// `/forecast/new` → `/forecast`) supaya halaman baru di menu otomatis terproteksi
// (CR v3.5 §2) — tidak ada lagi daftar manual yang bisa tertinggal.
const PROTECTED_PREFIXES = [
  ...new Set(NAV_GROUPS.flatMap((g) => g.items.map((i) => `/${i.href.split("/")[1]}`))),
];

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!isProtectedPath(pathname)) return NextResponse.next();

  const token = request.cookies.get(TOKEN_COOKIE)?.value;
  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  // Semua path kecuali login, aset Next, favicon, dan api — filter prefix di atas.
  matcher: ["/((?!login|_next|favicon.ico|api).*)"],
};
